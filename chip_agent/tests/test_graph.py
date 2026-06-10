from src.graph import build_graph
from langchain_core.messages import HumanMessage

def test_graph_routing():
    graph = build_graph()
    result = graph.invoke({"messages": [HumanMessage(content="What is N5 M3 pitch?")]})
    assert len(result["messages"]) > 1
    assert "PDK" in result["messages"][-1].content
