from src.experts.pdk_expert import pdk_expert_node
from langchain_core.messages import HumanMessage, AIMessage

def test_pdk_expert_node():
    state = {"messages": [HumanMessage(content="What is N5 M3 pitch?")]}
    result = pdk_expert_node(state)
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert "PDK" in result["messages"][0].content
