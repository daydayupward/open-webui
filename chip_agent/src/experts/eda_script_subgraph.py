import re
import operator
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, AIMessage

from src.utils import get_llm
from src.retrieval.eda_retriever import aretrieve_eda_manuals
from src.tools.eda_lint import lint_eda_script
from src.prompts.eda_prompt import EDA_SCRIPT_GENERATION_PROMPT, EDA_SCRIPT_REFINEMENT_PROMPT

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
    
    retrieval_res = await aretrieve_eda_manuals(query, metadata)
    
    chunks_data = [
        {"content": chunk.page_content, "metadata": chunk.metadata}
        for chunk in retrieval_res["chunks"]
    ]
    
    return {
        "retrieved_docs": chunks_data,
        "tool_logs": [retrieval_res["logs"]]
    }

async def generate_node(state: EDASubgraphState) -> dict:
    llm = get_llm(state.get("temperature") or 0.0)
    context_list = []
    for idx, doc in enumerate(state.get("retrieved_docs", [])):
        meta = doc.get("metadata") or {}
        source_name = meta.get("name") or meta.get("source") or "Document"
        context_list.append(f"[{idx + 1}] Source: {source_name}\nContent: {doc['content']}")
    context_str = "\n\n".join(context_list)
    if not context_str:
        context_str = "No specific reference manuals found."
        
    system_prompt = SystemMessage(
        content=EDA_SCRIPT_GENERATION_PROMPT.format(context=context_str)
    )
    
    messages = [system_prompt] + state.get("messages", [])
    response = await llm.ainvoke(messages)
    
    return {
        "previous_response": response.content,
        "messages": [response]
    }

async def lint_node(state: EDASubgraphState) -> dict:
    previous_response = state.get("previous_response", "")
    script = extract_script(previous_response)
    
    linter_res = lint_eda_script(script)
    current_iterations = state.get("iterations", 0) + 1
    
    log_entry = {
        "step": f"Linter Check (Iteration {current_iterations})",
        "script_extracted": script,
        "passed": linter_res["passed"],
        "issues": linter_res["issues"],
        "suggestions": linter_res["suggestions"]
    }
    
    return {
        "linter_result": linter_res,
        "iterations": current_iterations,
        "tool_logs": [log_entry]
    }

async def refine_node(state: EDASubgraphState) -> dict:
    llm = get_llm(state.get("temperature") or 0.0)
    query = state.get("query", "")
    previous_response = state.get("previous_response", "")
    linter_result = state.get("linter_result", {})
    
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
    
    messages = [system_prompt] + state.get("messages", [])
    response = await llm.ainvoke(messages)
    
    return {
        "previous_response": response.content,
        "messages": [response]
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
