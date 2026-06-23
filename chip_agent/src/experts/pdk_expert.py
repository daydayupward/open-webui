from langchain_core.messages import SystemMessage
from src.state import AgentState
from src.utils import get_llm
from src.retrieval.pdk_retriever import aretrieve_pdk_rules
from src.prompts.pdk_prompt import PDK_SYSTEM_PROMPT

async def pdk_expert_node(state: AgentState) -> dict:
    query = ""
    for msg in reversed(state.get("messages", [])):
        msg_type = getattr(msg, "type", None)
        if msg_type == "human" or msg.__class__.__name__ == "HumanMessage":
            query = msg.content
            break
            
    metadata = state.get("metadata", {})
    retrieval_res = await aretrieve_pdk_rules(query, metadata)
    
    chunks = retrieval_res["chunks"]
    logs = retrieval_res["logs"]
    
    context_list = []
    for idx, c in enumerate(chunks):
        source_name = c.metadata.get("name") or c.metadata.get("source") or "Document"
        context_list.append(f"[{idx + 1}] Source: {source_name}\nContent: {c.page_content}")
    context = "\n\n".join(context_list)
    if not context:
        context = "No database context found due to connection issue or missing match."
        
    llm = get_llm(state.get("temperature") or 0.0)
    system_prompt = SystemMessage(
        content=PDK_SYSTEM_PROMPT.format(context=context)
    )
    
    messages = [system_prompt] + state["messages"]
    response = await llm.ainvoke(messages)
    
    serializable_chunks = [c.model_dump() for c in chunks]
    
    return {
        "messages": [response],
        "retrieved_docs": serializable_chunks,
        "tool_logs": [logs]
    }
