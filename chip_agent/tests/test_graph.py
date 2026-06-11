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

@patch("src.utils.ChatOpenAI")
@patch("src.retrieval.pdk_retriever.query_vector_store")
def test_full_chain_pdk_execution(mock_query_store, mock_chat_openai):
    # Mock LLM for supervisor and pdk_expert
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        # Supervisor
        AIMessage(content='{"next": "pdk_expert", "metadata": {"category": "PDK", "node": "N5"}}'),
        # PDK Expert
        AIMessage(content="[PDK Expert] The M3 metal pitch for N5 process node is 36nm.")
    ]
    mock_chat_openai.return_value = mock_llm

    # Mock Vector Store search
    mock_doc = MagicMock()
    mock_doc.page_content = "The M3 metal pitch for N5 process node is 36nm."
    mock_doc.metadata = {"category": "PDK", "node": "N5"}
    mock_query_store.return_value = [mock_doc]

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

    # Verify state progression
    assert result["route"] == "pdk_expert"
    assert result["metadata"]["category"] == "PDK"
    assert result["metadata"]["node"] == "N5"
    assert result["final_answer"] == "[PDK Expert] The M3 metal pitch for N5 process node is 36nm."
    assert len(result["retrieved_docs"]) == 1
    assert result["retrieved_docs"][0]["page_content"] == "The M3 metal pitch for N5 process node is 36nm."
    assert len(result["tool_logs"]) == 1
    assert result["tool_logs"][0]["step"] == "PDK Retrieval"
