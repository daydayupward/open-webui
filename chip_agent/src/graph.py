import json
from typing import List
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage

from src.utils import get_llm
from src.state import AgentState
from src.experts.pdk_expert import pdk_expert_node
from src.experts.eda_script_expert import eda_script_expert_node
from src.experts.metrics_analyst import metrics_analyst_node

def supervisor_node(state: AgentState) -> dict:
    return {"messages": []}

def router(state: AgentState) -> str:
    llm = get_llm()
    system_prompt = SystemMessage(
        content="You are a supervisor routing agent. Analyze the conversation history and classify the user's intent into exactly one category. "
                "Output your decision in raw JSON format with a single key 'next' containing one of these values:\n"
                "- 'pdk_expert' (if the query is about PDK rules, pitch, layers, LVS/DRC constraints)\n"
                "- 'eda_script_expert' (if the query asks for EDA commands, Tcl/Skill script generation, Innovus, ICC2, or tool setups)\n"
                "- 'metrics_analyst' (if the query is about project metrics, PPA, timing reports, power/area history)\n"
                "- 'FINISH' (if the conversation is complete and the last assistant message has answered the user's query).\n\n"
                "Example response: {\"next\": \"pdk_expert\"}"
    )
    messages = [system_prompt] + state["messages"]
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            content = "".join([l for l in lines if not l.startswith("```")])
        data = json.loads(content)
        next_step = data.get("next", "FINISH")
        if next_step == "FINISH":
            return "finalizer"
        if next_step in ["pdk_expert", "eda_script_expert", "metrics_analyst"]:
            return next_step
    except Exception:
        pass
    return "pdk_expert"

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
