from langgraph.graph import StateGraph, END

from src.state import AgentState
from src.supervisor import arun_supervisor
from src.experts.pdk_expert import pdk_expert_node
from src.experts.eda_script_expert import eda_script_expert_node
from src.experts.metrics_analyst import metrics_analyst_node
from src.constants import ExpertRoute
from src.message_utils import get_last_ai_content

async def supervisor_node(state: AgentState) -> dict:
    res = await arun_supervisor(state.get("messages", []))
    update = {
        "route": res["route"],
        "metadata": res["metadata"]
    }
    if "messages" in res:
        update["messages"] = res["messages"]
    return update

def router(state: AgentState) -> str:
    return state.get("route", ExpertRoute.FINALIZER)

async def finalizer_node(state: AgentState) -> dict:
    final_text = get_last_ai_content(state.get("messages", []))
    if not final_text:
        final_text = "I am ready to assist. Please let me know how I can help with your physical design query."
        
    retrieved_docs = state.get("retrieved_docs", [])
    if retrieved_docs and final_text:
        import re
        existing_images = set(re.findall(r'!\[.*?\]\((/static/uploads/images/[^\s\)]+)\)', final_text))
        
        doc_images = []
        for doc in retrieved_docs:
            content = ""
            if isinstance(doc, dict):
                content = doc.get("content") or doc.get("page_content") or ""
            elif hasattr(doc, "page_content"):
                content = doc.page_content
                
            imgs = re.findall(r'!\[.*?\]\((/static/uploads/images/[^\s\)]+)\)', content)
            for img in imgs:
                if img not in doc_images and img not in existing_images:
                    doc_images.append(img)
                    
        if doc_images:
            image_md_blocks = "\n\n**相关图示**:\n" + "\n\n".join([f"![]({img})" for img in doc_images])
            if "**参考来源**" in final_text:
                final_text = final_text.replace("**参考来源**", f"{image_md_blocks}\n\n**参考来源**")
            elif "**相关问题**" in final_text:
                final_text = final_text.replace("**相关问题**", f"{image_md_blocks}\n\n**相关问题**")
            else:
                final_text += f"\n\n{image_md_blocks}"
                
    return {"final_answer": final_text}

def build_graph():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node(ExpertRoute.PDK, pdk_expert_node)
    workflow.add_node(ExpertRoute.EDA, eda_script_expert_node)
    workflow.add_node(ExpertRoute.METRICS, metrics_analyst_node)
    workflow.add_node(ExpertRoute.FINALIZER, finalizer_node)
    
    # Entry point
    workflow.set_entry_point("supervisor")
    
    # Supervisor routes to experts or finalizer
    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            ExpertRoute.PDK: ExpertRoute.PDK,
            ExpertRoute.EDA: ExpertRoute.EDA,
            ExpertRoute.METRICS: ExpertRoute.METRICS,
            ExpertRoute.FINALIZER: ExpertRoute.FINALIZER
        }
    )
    
    # Experts proceed to finalizer
    workflow.add_edge(ExpertRoute.PDK, ExpertRoute.FINALIZER)
    workflow.add_edge(ExpertRoute.EDA, ExpertRoute.FINALIZER)
    workflow.add_edge(ExpertRoute.METRICS, ExpertRoute.FINALIZER)
    
    # Finalizer ends workflow
    workflow.add_edge(ExpertRoute.FINALIZER, END)
    
    return workflow.compile()
