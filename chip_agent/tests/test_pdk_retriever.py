import pytest
from unittest.mock import patch, MagicMock
from src.retrieval.pdk_retriever import aretrieve_pdk_rules

@patch("src.vector_store.aquery_vector_store")
@patch("src.retrieval.base.QwenRerankerClient")
@pytest.mark.anyio
async def test_retrieve_pdk_rules_success(mock_reranker_class, mock_query_store):
    mock_doc = MagicMock()
    mock_doc.page_content = "Metal pitch rule"
    mock_doc.metadata = {"category": "PDK", "node": "N5"}
    mock_query_store.return_value = [mock_doc]
    
    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = lambda q, chunks, top_k: chunks
    mock_reranker_class.return_value = mock_reranker
    
    res = await aretrieve_pdk_rules("What is M3 pitch?", {"node": "n5"})
    
    assert res["logs"]["status"] == "success"
    assert len(res["chunks"]) == 1
    assert res["chunks"][0].page_content == "Metal pitch rule"
    
    mock_query_store.assert_called_once()
    called_filter = mock_query_store.call_args[1]["filter"]
    assert called_filter["category"] == {"$in": ["PDK"]}
    assert called_filter["node"] == "n5"

@patch("src.vector_store.aquery_vector_store")
@pytest.mark.anyio
async def test_retrieve_pdk_rules_fallback_on_db_error(mock_query_store):
    mock_query_store.side_effect = RuntimeError("Connection refused")
    
    res = await aretrieve_pdk_rules("What is M3 pitch?", {"node": "N5"})
    
    assert res["logs"]["status"] == "failed"
    assert "Connection refused" in res["logs"]["error"]
    assert len(res["chunks"]) == 0
