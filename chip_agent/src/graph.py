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
