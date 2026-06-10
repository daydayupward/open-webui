from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, AIMessage
from typing import TypedDict, List, Annotated
import operator
from src.experts.pdk_expert import pdk_expert_node

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]

def supervisor_node(state: AgentState) -> dict:
    # MVP Supervisor: blindly routes everything to PDK expert for now
    return {"messages": []}

def router(state: AgentState) -> str:
    # MVP Router: always returns "pdk_expert"
    return "pdk_expert"

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("pdk_expert", pdk_expert_node)
    
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges("supervisor", router, {"pdk_expert": "pdk_expert"})
    workflow.add_edge("pdk_expert", END)
    
    return workflow.compile()
