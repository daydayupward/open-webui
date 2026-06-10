from langgraph.graph import StateGraph, END

from src.state import AgentState
from src.supervisor import run_supervisor
from src.experts.pdk_expert import pdk_expert_node
from src.experts.eda_script_expert import eda_script_expert_node
from src.experts.metrics_analyst import metrics_analyst_node

def supervisor_node(state: AgentState) -> dict:
    res = run_supervisor(state.get("messages", []))
    return {
        "route": res["route"],
        "metadata": res["metadata"]
    }

def router(state: AgentState) -> str:
    return state.get("route", "finalizer")

def finalizer_node(state: AgentState) -> dict:
    final_text = ""
    for msg in reversed(state.get("messages", [])):
        msg_type = getattr(msg, "type", None)
        if msg_type == "ai" or msg.__class__.__name__ == "AIMessage":
            final_text = msg.content
            break
            
    if not final_text:
        final_text = "I am ready to assist. Please let me know how I can help with your physical design query."
        
    return {"final_answer": final_text}

def build_graph():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("pdk_expert", pdk_expert_node)
    workflow.add_node("eda_script_expert", eda_script_expert_node)
    workflow.add_node("metrics_analyst", metrics_analyst_node)
    workflow.add_node("finalizer", finalizer_node)
    
    # Entry point
    workflow.set_entry_point("supervisor")
    
    # Supervisor routes to experts or finalizer
    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "pdk_expert": "pdk_expert",
            "eda_script_expert": "eda_script_expert",
            "metrics_analyst": "metrics_analyst",
            "finalizer": "finalizer"
        }
    )
    
    # Experts proceed to finalizer
    workflow.add_edge("pdk_expert", "finalizer")
    workflow.add_edge("eda_script_expert", "finalizer")
    workflow.add_edge("metrics_analyst", "finalizer")
    
    # Finalizer ends workflow
    workflow.add_edge("finalizer", END)
    
    return workflow.compile()
