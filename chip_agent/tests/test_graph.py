from unittest.mock import patch, MagicMock
from src.graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage

@patch("src.graph.get_llm")
@patch("src.graph.pdk_expert_node")
@patch("src.graph.eda_script_expert_node")
@patch("src.graph.metrics_analyst_node")
def test_graph_routing(mock_metrics, mock_eda, mock_pdk, mock_get_llm):
    # Mock routing LLM calls (only one call needed in single-pass layout)
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content='{"next": "pdk_expert"}')
    mock_get_llm.return_value = mock_llm

    # Mock PDK expert implementation
    mock_pdk.return_value = {"messages": [AIMessage(content="[PDK Expert] The metal pitch is 36nm.")]}

    graph = build_graph()
    initial_state = {
        "messages": [HumanMessage(content="What is N5 M3 pitch?")],
        "request_id": "test-req-id",
        "route": "",
        "metadata": {},
        "retrieved_docs": [],
        "tool_logs": [],
        "final_answer": "",
        "errors": []
    }
    result = graph.invoke(initial_state)
    
    assert "messages" in result
    assert result["final_answer"] == "[PDK Expert] The metal pitch is 36nm."
    mock_pdk.assert_called_once()
    # In single-pass pipeline, supervisor LLM is invoked exactly once
    mock_llm.invoke.assert_called_once()
