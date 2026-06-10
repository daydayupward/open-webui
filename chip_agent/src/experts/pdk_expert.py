from typing import TypedDict, List
from langchain_core.messages import AnyMessage, AIMessage

class AgentState(TypedDict):
    messages: List[AnyMessage]

def pdk_expert_node(state: AgentState) -> dict:
    query = state["messages"][-1].content
    # MVP: Mock retrieval and response. In production, this calls the VectorStore from Task 2.
    mock_response = f"[PDK Expert] Processed query: {query}. The M3 pitch for N5 is 36nm."
    return {"messages": [AIMessage(content=mock_response)]}
