from unittest.mock import patch, MagicMock
from src.graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage

@patch("src.graph.run_supervisor")
@patch("src.graph.pdk_expert_node")
@patch("src.graph.eda_script_expert_node")
@patch("src.graph.metrics_analyst_node")
def test_graph_routing(mock_metrics, mock_eda, mock_pdk, mock_run_supervisor):
    # Mock supervisor return values
    mock_run_supervisor.return_value = {
        "route": "pdk_expert",
        "metadata": {
            "category": "PDK",
            "node": "N5",
            "tool": None,
            "project_id": None,
            "confidence": 1.0,
            "missing_fields": []
        }
    }

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
    assert result["route"] == "pdk_expert"
    assert result["metadata"]["category"] == "PDK"
    assert result["metadata"]["node"] == "N5"
    assert result["final_answer"] == "[PDK Expert] The metal pitch is 36nm."
    mock_pdk.assert_called_once()
    mock_run_supervisor.assert_called_once()
