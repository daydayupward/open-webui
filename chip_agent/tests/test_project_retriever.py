import pytest
from unittest.mock import patch, MagicMock
from src.retrieval.project_retriever import retrieve_project_docs


@patch("src.retrieval.project_retriever.query_vector_store")
@patch("src.retrieval.project_retriever.QwenRerankerClient")
def test_retrieve_project_docs_success(mock_reranker_class, mock_query_store):
    """Test successful retrieval with project_id filtering."""
    mock_doc = MagicMock()
    mock_doc.page_content = "Project design specification"
    mock_doc.metadata = {"category": "PROJECT", "project_id": "proj-123", "doc_type": "spec"}
    mock_query_store.return_value = [mock_doc]

    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = lambda q, chunks, top_k: chunks
    mock_reranker_class.return_value = mock_reranker

    res = retrieve_project_docs("What is the design spec?", "proj-123")

    assert res["logs"]["status"] == "success"
    assert len(res["chunks"]) == 1
    assert res["chunks"][0].page_content == "Project design specification"
    assert res["logs"]["project_id"] == "proj-123"

    mock_query_store.assert_called_once()
    called_filter = mock_query_store.call_args[1]["filter"]
    assert called_filter["category"] == "PROJECT"
    assert called_filter["project_id"] == "proj-123"


@patch("src.retrieval.project_retriever.query_vector_store")
@patch("src.retrieval.project_retriever.QwenRerankerClient")
def test_retrieve_project_docs_with_metadata(mock_reranker_class, mock_query_store):
    """Test retrieval with additional metadata filtering."""
    mock_doc = MagicMock()
    mock_doc.page_content = "Meeting notes"
    mock_doc.metadata = {"category": "PROJECT", "project_id": "proj-456", "doc_type": "meeting"}
    mock_query_store.return_value = [mock_doc]

    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = lambda q, chunks, top_k: chunks
    mock_reranker_class.return_value = mock_reranker

    res = retrieve_project_docs(
        "What were the meeting decisions?",
        "proj-456",
        metadata={"doc_type": "meeting"}
    )

    assert res["logs"]["status"] == "success"
    assert len(res["chunks"]) == 1

    called_filter = mock_query_store.call_args[1]["filter"]
    assert called_filter["category"] == "PROJECT"
    assert called_filter["project_id"] == "proj-456"
    assert called_filter["doc_type"] == "meeting"


@patch("src.retrieval.project_retriever.query_vector_store")
@patch("src.retrieval.project_retriever.QwenRerankerClient")
def test_retrieve_project_docs_multiple_results(mock_reranker_class, mock_query_store):
    """Test retrieval returns multiple results."""
    mock_docs = []
    for i in range(3):
        mock_doc = MagicMock()
        mock_doc.page_content = f"Document {i}"
        mock_doc.metadata = {"category": "PROJECT", "project_id": "proj-789"}
        mock_docs.append(mock_doc)
    mock_query_store.return_value = mock_docs

    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = lambda q, chunks, top_k: chunks[:top_k]
    mock_reranker_class.return_value = mock_reranker

    res = retrieve_project_docs("project overview", "proj-789", top_k=2)

    assert res["logs"]["status"] == "success"
    assert res["logs"]["retrieved_count"] == 3
    assert res["logs"]["reranked_count"] == 2


def test_retrieve_project_docs_missing_project_id():
    """Test that missing project_id raises ValueError."""
    with pytest.raises(ValueError, match="project_id is required"):
        retrieve_project_docs("some query", "")


def test_retrieve_project_docs_none_project_id():
    """Test that None project_id raises ValueError."""
    with pytest.raises(ValueError, match="project_id is required"):
        retrieve_project_docs("some query", None)


@patch("src.retrieval.project_retriever.query_vector_store")
def test_retrieve_project_docs_db_error(mock_query_store):
    """Test graceful handling of database errors."""
    mock_query_store.side_effect = RuntimeError("Connection refused")

    res = retrieve_project_docs("What is the design spec?", "proj-123")

    assert res["logs"]["status"] == "failed"
    assert "Connection refused" in res["logs"]["error"]
    assert len(res["chunks"]) == 0


@patch("src.retrieval.project_retriever.query_vector_store")
@patch("src.retrieval.project_retriever.QwenRerankerClient")
def test_retrieve_project_docs_empty_results(mock_reranker_class, mock_query_store):
    """Test retrieval with no matching documents."""
    mock_query_store.return_value = []

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = []
    mock_reranker_class.return_value = mock_reranker

    res = retrieve_project_docs("nonexistent query", "proj-123")

    assert res["logs"]["status"] == "success"
    assert res["logs"]["retrieved_count"] == 0
    assert res["logs"]["reranked_count"] == 0
    assert len(res["chunks"]) == 0


@patch("src.retrieval.project_retriever.query_vector_store")
@patch("src.retrieval.project_retriever.QwenRerankerClient")
def test_retrieve_project_docs_logs_structure(mock_reranker_class, mock_query_store):
    """Test that logs contain all expected fields."""
    mock_query_store.return_value = []

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = []
    mock_reranker_class.return_value = mock_reranker

    res = retrieve_project_docs("test query", "proj-123", fetch_k=15, top_k=5)

    logs = res["logs"]
    assert logs["step"] == "Project Retrieval"
    assert logs["query"] == "test query"
    assert logs["project_id"] == "proj-123"
    assert logs["fetch_k"] == 15
    assert logs["top_k"] == 5
    assert logs["status"] == "success"
    assert logs["error"] is None
