import logging
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.state import AgentState
from src.utils import get_llm
from src.retrieval.pdk_retriever import aretrieve_pdk_rules
from src.prompts.pdk_prompt import PDK_SYSTEM_PROMPT
from src.evaluators import (
    grade_document_relevance,
    grade_hallucination,
    grade_answer_completeness,
    rewrite_query
)

logger = logging.getLogger(__name__)

async def pdk_expert_node(state: AgentState) -> dict:
    original_query = ""
    for msg in reversed(state.get("messages", [])):
        msg_type = getattr(msg, "type", None)
        if msg_type == "human" or msg.__class__.__name__ == "HumanMessage":
            original_query = msg.content
            break
            
    metadata = state.get("metadata", {})
    llm = get_llm(state.get("temperature") or 0.0)
    
    # Self-RAG: Retrieve and Grade Documents, Rewrite if necessary
    current_query = original_query
    max_retries = 2
    relevant_chunks = []
    all_logs = []
    
    for i in range(max_retries + 1):
        logger.info("[Self-RAG PDK] Retrieval attempt %d with query: '%s'", i+1, current_query)
        retrieval_res = await aretrieve_pdk_rules(current_query, metadata)
        chunks = retrieval_res.get("chunks", [])
        logs = retrieval_res.get("logs", {})
        all_logs.append(logs)
        
        logger.info("[Self-RAG PDK] Grading %d retrieved documents...", len(chunks))
        relevant_chunks = []
        for c in chunks:
            is_relevant = await grade_document_relevance(c.page_content, original_query)
            if is_relevant:
                relevant_chunks.append(c)
                
        logger.info("[Self-RAG PDK] Found %d/%d relevant chunks", len(relevant_chunks), len(chunks))
        
        if len(relevant_chunks) > 0:
            break
            
        if i < max_retries:
            logger.info("[Self-RAG PDK] No relevant documents found. Rewriting query...")
            current_query = await rewrite_query(original_query)
        else:
            logger.info("[Self-RAG PDK] Exhausted query rewriting. Using all retrieved chunks as fallback.")
            relevant_chunks = chunks
            
    # Self-RAG: Generate and Grade Answer
    max_generation_attempts = 0
    final_response = None
    
    from langchain_core.messages import AIMessage, HumanMessage
    local_messages = []
    for m in state.get("messages", []):
        if isinstance(m, AIMessage):
            content = m.content
            for marker in ("**参考来源**:", "**参考来源**：", "**相关问题**:", "**相关问题**：", "追问"):
                if marker in content:
                    content = content.split(marker)[0]
            local_messages.append(AIMessage(content=content.strip()))
        else:
            local_messages.append(m)
    
    for j in range(max_generation_attempts + 1):
        context_list = []
        for idx, c in enumerate(relevant_chunks):
            source_name = c.metadata.get("name") or c.metadata.get("source") or "Document"
            context_list.append(f"[{idx + 1}] Source: {source_name}\nContent: {c.page_content}")
        context = "\n\n".join(context_list)
        if not context:
            context = "No database context found due to connection issue or missing match."
            
        system_prompt = SystemMessage(
            content=PDK_SYSTEM_PROMPT.format(context=context)
        )
        
        messages = [system_prompt] + local_messages
        
        logger.info("[Self-RAG PDK] Generating answer (attempt %d)...", j+1)
        response = await llm.ainvoke(messages)
        
        if not relevant_chunks:
            final_response = response
            break
            
        is_grounded = await grade_hallucination(response.content, relevant_chunks)
        is_complete = await grade_answer_completeness(response.content, original_query)
        
        if is_grounded and is_complete:
            logger.info("[Self-RAG PDK] Answer passed all validation checks.")
            final_response = response
            break
            
        if j < max_generation_attempts:
            logger.warning("[Self-RAG PDK] Answer failed validation checks. Grounded: %s, Complete: %s", is_grounded, is_complete)
            feedback_prompt = (
                "\n\n[System Alert]: Your previous response did not fully answer the user's question or contained "
                "hallucinations not supported by the context. Please rewrite the response, sticking strictly "
                "to the retrieved documents and ensuring all parts of the user's question are answered."
            )
            local_messages = local_messages + [AIMessage(content=response.content), HumanMessage(content=feedback_prompt)]
        else:
            logger.warning("[Self-RAG PDK] Generation grading failed but retry limit reached.")
            final_response = response
            
    serializable_chunks = [c.model_dump() for c in relevant_chunks]
    
    # Save Trace to Observability Database
    try:
        import uuid
        from src.admin_db import save_trace
        trace_id = state.get("request_id") or str(uuid.uuid4())
        save_trace(
            trace_id=trace_id,
            query=original_query,
            rewritten_query=current_query,
            chunks=serializable_chunks,
            answer=final_response.content if final_response else ""
        )
    except Exception as e:
        logger.error("Failed to save query trace to SQLite: %s", e)
    
    return {
        "messages": [final_response],
        "retrieved_docs": serializable_chunks,
        "tool_logs": all_logs
    }
