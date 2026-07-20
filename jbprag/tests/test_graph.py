from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from src.graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage

@patch("src.graph.arun_supervisor")
@patch("src.graph.pdk_expert_node")
@patch("src.graph.eda_script_expert_node")
@patch("src.graph.metrics_analyst_node")
@pytest.mark.anyio
async def test_graph_routing(mock_metrics, mock_eda, mock_pdk, mock_arun_supervisor):
    # Mock supervisor return values
    mock_arun_supervisor.return_value = {
        "route": "pdk_expert",
        "metadata": {
            "categories": ["PDK"],
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
    result = await graph.ainvoke(initial_state)
    
    assert "messages" in result
    assert result["route"] == "pdk_expert"
    assert "PDK" in result["metadata"]["categories"]
    assert result["metadata"]["node"] == "N5"
    assert result["final_answer"] == "[PDK Expert] The metal pitch is 36nm."
    mock_pdk.assert_called_once()
    mock_arun_supervisor.assert_called_once()

@patch("src.experts.pdk_expert.rewrite_query", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_answer_completeness", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_hallucination", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_document_relevance", new_callable=AsyncMock)
@patch("src.utils.ChatOpenAI")
@patch("src.vector_store.aquery_vector_store")
@pytest.mark.anyio
async def test_full_chain_pdk_execution(mock_query_store, mock_chat_openai, mock_relevance, mock_hallucination, mock_completeness, mock_rewrite):
    # Mock LLM for supervisor and pdk_expert
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        # Supervisor
        AIMessage(content='{"next": "pdk_expert", "metadata": {"categories": ["PDK"], "node": "N5"}}'),
        # PDK Expert
        AIMessage(content="[PDK Expert] The M3 metal pitch for N5 process node is 36nm.")
    ]
    mock_chat_openai.return_value = mock_llm

    # Mock Evaluators
    mock_relevance.return_value = True
    mock_hallucination.return_value = True
    mock_completeness.return_value = True
    mock_rewrite.side_effect = lambda q: q

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
    result = await graph.ainvoke(initial_state)

    # Verify state progression
    assert result["route"] == "pdk_expert"
    assert "PDK" in result["metadata"]["categories"]
    assert result["metadata"]["node"] == "N5"
    assert result["final_answer"] == "[PDK Expert] The M3 metal pitch for N5 process node is 36nm."
    assert len(result["retrieved_docs"]) == 1
    assert result["retrieved_docs"][0]["page_content"] == "The M3 metal pitch for N5 process node is 36nm."
    assert len(result["tool_logs"]) == 1
    assert result["tool_logs"][0]["step"] == "PDK Retrieval"
