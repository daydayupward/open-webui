import re
import operator
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, AIMessage, HumanMessage

from src.utils import get_llm
from src.retrieval.eda_retriever import aretrieve_eda_manuals
from src.tools.eda_lint import lint_eda_script
from src.prompts.eda_prompt import EDA_SCRIPT_GENERATION_PROMPT, EDA_SCRIPT_REFINEMENT_PROMPT, EDA_SCRIPT_REVIEW_PROMPT
from src.evaluators import (
    grade_document_relevance,
    grade_hallucination,
    grade_answer_completeness,
    rewrite_query
)

class EDASubgraphState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    query: str
    metadata: Dict[str, Any]
    retrieved_docs: Annotated[List[Dict[str, Any]], operator.add]
    tool_logs: Annotated[List[Dict[str, Any]], operator.add]
    iterations: int
    linter_result: Dict[str, Any]
    previous_response: str
    final_answer: str
    temperature: float

def extract_script(content: str) -> str:
    """Extracts code block content from markdown formatting if present."""
    match = re.search(r"```(?:tcl|skill)?\n(.*?)```", content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return content.strip()

async def retrieve_node(state: EDASubgraphState) -> dict:
    query = state.get("query", "")
    metadata = state.get("metadata", {})
    
    try:
        current_query = await rewrite_query(query)
    except Exception:
        current_query = query
    max_retries = 2
    relevant_chunks = []
    all_logs = []
    
    for i in range(max_retries + 1):
        retrieval_res = await aretrieve_eda_manuals(current_query, metadata)
        chunks = retrieval_res.get("chunks", [])
        all_logs.append(retrieval_res.get("logs", {}))
        
        relevant_chunks = []
        for c in chunks:
            is_relevant = await grade_document_relevance(c.page_content, query)
            if is_relevant:
                relevant_chunks.append(c)
                
        if len(relevant_chunks) > 0:
            break
            
        if i < max_retries:
            current_query = await rewrite_query(query)
        else:
            relevant_chunks = chunks
            
    chunks_data = [
        {"content": chunk.page_content, "metadata": chunk.metadata}
        for chunk in relevant_chunks
    ]
    
    return {
        "retrieved_docs": chunks_data,
        "tool_logs": all_logs
    }

async def generate_node(state: EDASubgraphState) -> dict:
    llm = get_llm(state.get("temperature") or 0.0)
    context_list = []
    retrieved_docs = state.get("retrieved_docs", [])
    for idx, doc in enumerate(retrieved_docs):
        meta = doc.get("metadata") or {}
        source_name = meta.get("name") or meta.get("source") or "Document"
        context_list.append(f"[{idx + 1}] Source: {source_name}\nContent: {doc['content']}")
    context_str = "\n\n".join(context_list)
    if not context_str:
        context_str = "No specific reference manuals found."
        
    system_prompt = SystemMessage(
        content=EDA_SCRIPT_GENERATION_PROMPT.format(context=context_str)
    )
    
    max_attempts = 0
    from langchain_core.messages import AIMessage, HumanMessage
    import re as _re
    local_messages = []
    for m in state.get("messages", []):
        if isinstance(m, AIMessage):
            content = m.content
            for marker in ("**参考来源**:", "**参考来源**：", "**相关问题**:", "**相关问题**：", "**相关图示**:", "追问"):
                if marker in content:
                    content = content.split(marker)[0]
            content = _re.sub(r'\n\d+\.\s+.{10,}\??\s*$', '', content.strip())
            if len(content) > 2000:
                content = content[:2000] + "..."
            local_messages.append(AIMessage(content=content.strip()))
        else:
            local_messages.append(m)
    final_response = None
    
    for i in range(max_attempts + 1):
        messages = [system_prompt] + local_messages
        response = await llm.ainvoke(messages)
        
        if not retrieved_docs:
            final_response = response
            break
            
        docs_for_grading = [d["content"] for d in retrieved_docs]
        is_grounded = await grade_hallucination(response.content, docs_for_grading)
        is_complete = await grade_answer_completeness(response.content, state.get("query", ""))
        
        if is_grounded and is_complete:
            final_response = response
            break
            
        if i < max_attempts:
            feedback_prompt = (
                "\n\n[System Alert]: Your generated script did not fully satisfy the query "
                "or contained inconsistencies with the reference manual. Please refine the script, "
                "ensuring all parts of the user request are implemented and strictly matching the reference manual."
            )
            local_messages = local_messages + [AIMessage(content=response.content), HumanMessage(content=feedback_prompt)]
        else:
            final_response = response

    # Post-process: clean up "相关问题" section to only keep 3 concise questions
    import re as _re
    if final_response and final_response.content:
        rq_match = _re.search(r'\*\*相关问题\*\*[：:]\s*\n([\s\S]*)', final_response.content)
        if rq_match:
            body_before = final_response.content[:rq_match.start()]
            rq_block = rq_match.group(1)
            questions = _re.findall(r'^\s*\d+\.\s+.+', rq_block, _re.MULTILINE)
            questions = [q.strip() for q in questions[:3]]
            if questions:
                cleaned_rq = "**相关问题**:\n" + "\n".join(questions)
                final_response = AIMessage(content=body_before.rstrip() + "\n\n" + cleaned_rq)

    return {
        "previous_response": final_response.content,
        "messages": [final_response]
    }

async def review_script(query: str, context: str, script: str) -> dict:
    """Uses LLM to perform Code Review on the generated EDA script."""
    llm = get_llm(temperature=0.0)
    messages = [
        SystemMessage(content="You are a strict EDA script reviewer. Output only JSON."),
        HumanMessage(content=EDA_SCRIPT_REVIEW_PROMPT.format(
            query=query,
            context=context,
            script=script
        ))
    ]
    try:
        from src.supervisor import parse_json_safely
        response = await llm.ainvoke(messages)
        parsed = parse_json_safely(response.content)
        return {
            "passed": parsed.get("passed", True),
            "issues": parsed.get("issues", []),
            "suggestions": parsed.get("suggestions", [])
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("LLM script review failed: %s", e)
        return {"passed": True, "issues": [], "suggestions": []}

async def lint_node(state: EDASubgraphState) -> dict:
    previous_response = state.get("previous_response", "")
    script = extract_script(previous_response)
    
    # 1. Programmatic linter check
    linter_res = lint_eda_script(script)
    
    # 2. LLM Joint Code Review
    context_list = []
    for idx, doc in enumerate(state.get("retrieved_docs", [])):
        context_list.append(f"[{idx + 1}] Content: {doc['content']}")
    context_str = "\n\n".join(context_list)
    if not context_str:
        context_str = "No specific reference manuals found."
        
    review_res = await review_script(state.get("query", ""), context_str, script)
    
    # Merge programmatic linter issues and LLM review feedback
    all_issues = linter_res.get("issues", []) + review_res.get("issues", [])
    all_suggestions = linter_res.get("suggestions", []) + review_res.get("suggestions", [])
    passed = linter_res.get("passed", True) and review_res.get("passed", True)
    
    current_iterations = state.get("iterations", 0) + 1
    
    log_entry = {
        "step": f"Linter & LLM Review (Iteration {current_iterations})",
        "script_extracted": script,
        "passed": passed,
        "issues": all_issues,
        "suggestions": all_suggestions
    }
    
    return {
        "linter_result": {
            "passed": passed,
            "issues": all_issues,
            "suggestions": all_suggestions
        },
        "iterations": current_iterations,
        "tool_logs": [log_entry]
    }

async def refine_node(state: EDASubgraphState) -> dict:
    llm = get_llm(state.get("temperature") or 0.0)
    query = state.get("query", "")
    previous_response = state.get("previous_response", "")
    linter_result = state.get("linter_result", {})
    retrieved_docs = state.get("retrieved_docs", [])
    
    issues_str = "\n".join(f"- {issue}" for issue in linter_result.get("issues", []))
    suggestions_str = "\n".join(f"- {sug}" for sug in linter_result.get("suggestions", []))
    
    system_prompt = SystemMessage(
        content=EDA_SCRIPT_REFINEMENT_PROMPT.format(
            query=query,
            previous_response=previous_response,
            linter_issues=issues_str,
            linter_suggestions=suggestions_str
        )
    )
    
    max_attempts = 2
    local_messages = list(state.get("messages", []))
    final_response = None
    
    for i in range(max_attempts + 1):
        messages = [system_prompt] + local_messages
        response = await llm.ainvoke(messages)
        
        if not retrieved_docs:
            final_response = response
            break
            
        docs_for_grading = [d["content"] for d in retrieved_docs]
        is_grounded = await grade_hallucination(response.content, docs_for_grading)
        is_complete = await grade_answer_completeness(response.content, query)
        
        if is_grounded and is_complete:
            final_response = response
            break
            
        if i < max_attempts:
            feedback_prompt = (
                "\n\n[System Alert]: Your refined script still did not fully satisfy the query "
                "or contained inconsistencies with the reference manual. Please refine the script further, "
                "ensuring all parts of the user request are implemented and strictly matching the reference manual."
            )
            local_messages = local_messages + [AIMessage(content=response.content), HumanMessage(content=feedback_prompt)]
        else:
            final_response = response
            
    return {
        "previous_response": final_response.content,
        "messages": [final_response]
    }

async def finalize_node(state: EDASubgraphState) -> dict:
    return {
        "final_answer": state.get("previous_response", "")
    }

def route_after_lint(state: EDASubgraphState) -> str:
    linter_res = state.get("linter_result", {})
    iterations = state.get("iterations", 0)
    
    if linter_res.get("passed", False):
        return "finalize"
    elif iterations >= 2:
        return "finalize"
    else:
        return "refine"

def build_eda_subgraph():
    workflow = StateGraph(EDASubgraphState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("lint", lint_node)
    workflow.add_node("refine", refine_node)
    workflow.add_node("finalize", finalize_node)
    
    # Set entry point
    workflow.set_entry_point("retrieve")
    
    # Define edges
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "lint")
    
    workflow.add_conditional_edges(
        "lint",
        route_after_lint,
        {
            "refine": "refine",
            "finalize": "finalize"
        }
    )
    
    workflow.add_edge("refine", "lint")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()
