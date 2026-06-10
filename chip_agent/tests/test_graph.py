from unittest.mock import patch, MagicMock
from src.graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage

@patch("src.graph.get_llm")
@patch("src.graph.pdk_expert_node")
@patch("src.graph.eda_script_expert_node")
@patch("src.graph.metrics_analyst_node")
def test_graph_routing(mock_metrics, mock_eda, mock_pdk, mock_get_llm):
    # Mock routing LLM calls
    mock_llm = MagicMock()
    # Return sequence: PDK first, then FINISH
    mock_llm.invoke.side_effect = [
        AIMessage(content='{"next": "pdk_expert"}'),
        AIMessage(content='{"next": "FINISH"}')
    ]
    mock_get_llm.return_value = mock_llm

    # Mock PDK expert implementation
    mock_pdk.return_value = {"messages": [AIMessage(content="[PDK Expert] The metal pitch is 36nm.")]}

    graph = build_graph()
    result = graph.invoke({"messages": [HumanMessage(content="What is N5 M3 pitch?")]})
    
    assert len(result["messages"]) > 1
    assert "[PDK Expert]" in result["messages"][-1].content
    mock_pdk.assert_called_once()
