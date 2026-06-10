import json
import operator
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage

from src.utils import get_llm
from src.experts.pdk_expert import pdk_expert_node
from src.experts.eda_script_expert import eda_script_expert_node
from src.experts.metrics_analyst import metrics_analyst_node

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]

def supervisor_node(state: AgentState) -> dict:
    # Supervisor does not append anything by default, it acts as a routing anchor
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
        if next_step in ["pdk_expert", "eda_script_expert", "metrics_analyst", "FINISH"]:
            return next_step
    except Exception:
        pass
    return "pdk_expert"

def build_graph():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("pdk_expert", pdk_expert_node)
    workflow.add_node("eda_script_expert", eda_script_expert_node)
    workflow.add_node("metrics_analyst", metrics_analyst_node)
    
    # Entry point
    workflow.set_entry_point("supervisor")
    
    # Supervisor routes to experts or FINISH
    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "pdk_expert": "pdk_expert",
            "eda_script_expert": "eda_script_expert",
            "metrics_analyst": "metrics_analyst",
            "FINISH": END
        }
    )
    
    # Experts return to supervisor
    workflow.add_edge("pdk_expert", "supervisor")
    workflow.add_edge("eda_script_expert", "supervisor")
    workflow.add_edge("metrics_analyst", "supervisor")
    
    return workflow.compile()
