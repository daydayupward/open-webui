import json
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from langchain_core.messages import AIMessage
from src.retrieval.types import RetrievalChunk

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_evaluators():
    with patch("src.experts.pdk_expert.grade_document_relevance", return_value=True), \
         patch("src.experts.pdk_expert.grade_hallucination", return_value=True), \
         patch("src.experts.pdk_expert.grade_answer_completeness", return_value=True), \
         patch("src.experts.pdk_expert.rewrite_query", side_effect=lambda q: q), \
         patch("src.experts.eda_script_subgraph.grade_document_relevance", return_value=True), \
         patch("src.experts.eda_script_subgraph.grade_hallucination", return_value=True), \
         patch("src.experts.eda_script_subgraph.grade_answer_completeness", return_value=True), \
         patch("src.experts.eda_script_subgraph.rewrite_query", side_effect=lambda q: q), \
         patch("src.experts.eda_script_subgraph.review_script", return_value={"passed": True, "issues": [], "suggestions": []}), \
         patch("src.experts.metrics_subgraph.grade_document_relevance", return_value=True), \
         patch("src.experts.metrics_subgraph.grade_hallucination", return_value=True), \
         patch("src.experts.metrics_subgraph.grade_answer_completeness", return_value=True), \
         patch("src.experts.metrics_subgraph.rewrite_query", side_effect=lambda q: q):
        yield

def get_conflict_samples():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "conflict_samples.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def conflict_samples():
    return get_conflict_samples()

@patch("src.experts.pdk_expert.rewrite_query", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_answer_completeness", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_hallucination", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_document_relevance", new_callable=AsyncMock)
@patch("src.utils.ChatOpenAI")
@patch("src.vector_store.aquery_vector_store")
@pytest.mark.anyio
async def test_pdk_end_to_end_smoke(mock_query_store, mock_chat_openai, mock_relevance, mock_hallucination, mock_completeness, mock_rewrite, conflict_samples):
    # Mock LLM for supervisor and pdk expert
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        # Supervisor
        AIMessage(content='{"next": "pdk_expert", "metadata": {"category": "PDK", "node": "N5"}}'),
        # PDK Expert
        AIMessage(content="[PDK Expert] The M3 metal pitch for N5 process node is 36nm.")
    ]
    mock_chat_openai.return_value = mock_llm
    
    mock_relevance.return_value = True
    mock_hallucination.return_value = True
    mock_completeness.return_value = True
    mock_rewrite.side_effect = lambda q: q

    # Mock Vector Store search
    mock_doc = MagicMock()
    mock_doc.page_content = "The M3 metal pitch for N5 process node is 36nm. This ensures optimal routing density."
    mock_doc.metadata = conflict_samples["pdk"]["n5"]["metadata"]
    mock_query_store.return_value = [mock_doc]

    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": conflict_samples["pdk"]["n5"]["query"]}]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    content = data["choices"][0]["message"]["content"]
    assert "36nm" in content
    assert "N5" in content

@patch("src.utils.ChatOpenAI")
@patch("src.vector_store.aquery_vector_store")
@pytest.mark.anyio
async def test_eda_end_to_end_smoke(mock_query_store, mock_chat_openai, conflict_samples):
    # Mock LLM for supervisor and eda script generator
    from unittest.mock import AsyncMock
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        # Supervisor
        AIMessage(content='{"next": "eda_script_expert", "metadata": {"category": "EDA", "tool": "Innovus"}}'),
        # EDA Generator (returns a valid script)
        AIMessage(content="```tcl\nfloorPlan -site core -r 1 0.7 10 10 10 10\n```")
    ]
    mock_chat_openai.return_value = mock_llm

    # Mock Vector Store search
    mock_doc = MagicMock()
    mock_doc.page_content = "Innovus command 'floorPlan': Configures floorplan boundaries..."
    mock_doc.metadata = conflict_samples["eda"]["innovus"]["metadata"]
    mock_query_store.return_value = [mock_doc]

    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": conflict_samples["eda"]["innovus"]["query"]}]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    content = data["choices"][0]["message"]["content"]
    assert "floorPlan" in content

@patch("src.utils.ChatOpenAI")
@patch("src.experts.metrics_subgraph.aexecute_read_query")
@patch("src.experts.metrics_subgraph.validate_sql_query")
@patch("src.experts.metrics_subgraph.aretrieve_project_docs")
@pytest.mark.anyio
async def test_metrics_end_to_end_smoke(mock_retrieve, mock_validate, mock_execute, mock_chat_openai, conflict_samples):
    # Mock LLM:
    # 1. Supervisor
    # 2. Metrics Subgraph Route Classification (routed to sql)
    # 3. Metrics Subgraph SQL Generation
    # 4. Metrics Subgraph Summarization
    from unittest.mock import AsyncMock
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        # Supervisor
        AIMessage(content='{"next": "metrics_analyst", "metadata": {"category": "Project_Doc", "project_id": "Proj_A"}}'),
        # Route
        AIMessage(content="sql"),
        # SQL Generator
        AIMessage(content="SELECT wns, tns FROM project_metrics WHERE project_id = 'Proj_A';"),
        # Summarizer
        AIMessage(content="For Proj_A: WNS is 0.02, TNS is 0.00, power is 1.30, area is 4.50.")
    ]
    mock_chat_openai.return_value = mock_llm
    
    mock_validate.return_value = True
    mock_execute.return_value = [
        {"project_id": "Proj_A", "wns": 0.02, "tns": 0.00, "power": 1.30, "area": 4.50}
    ]

    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": conflict_samples["metrics"]["proj_a"]["query"]}]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    content = data["choices"][0]["message"]["content"]
    assert "Proj_A" in content
    assert "0.02" in content

@patch("src.experts.pdk_expert.rewrite_query", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_answer_completeness", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_hallucination", new_callable=AsyncMock)
@patch("src.experts.pdk_expert.grade_document_relevance", new_callable=AsyncMock)
@patch("src.utils.ChatOpenAI")
@patch("src.vector_store.aquery_vector_store")
@pytest.mark.anyio
async def test_postgres_unavailability_downgrade(mock_query_store, mock_chat_openai, mock_relevance, mock_hallucination, mock_completeness, mock_rewrite, conflict_samples):
    # Mock LLM for supervisor and pdk expert (handling error case)
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        # Supervisor
        AIMessage(content='{"next": "pdk_expert", "metadata": {"category": "PDK", "node": "N5"}}'),
        # PDK Expert: receives empty context message
        AIMessage(content="[PDK Expert] I could not retrieve PDK rules due to a temporary database connection error.")
    ]
    mock_chat_openai.return_value = mock_llm
    
    mock_relevance.return_value = True
    mock_hallucination.return_value = True
    mock_completeness.return_value = True
    mock_rewrite.side_effect = lambda q: q

    # Mock Vector Store search to raise connection exception
    mock_query_store.side_effect = Exception("PostgreSQL connection refused")

    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": conflict_samples["pdk"]["n5"]["query"]}]}
    )
    
    # Verify that the service does not return a 500 error but handles the error gracefully
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    content = data["choices"][0]["message"]["content"]
    assert "error" in content or "database" in content or "connection" in content
