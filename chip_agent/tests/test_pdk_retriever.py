from unittest.mock import patch, MagicMock
from src.retrieval.pdk_retriever import retrieve_pdk_rules

@patch("src.retrieval.pdk_retriever.query_vector_store")
@patch("src.retrieval.pdk_retriever.QwenRerankerClient")
def test_retrieve_pdk_rules_success(mock_reranker_class, mock_query_store):
    mock_doc = MagicMock()
    mock_doc.page_content = "Metal pitch rule"
    mock_doc.metadata = {"category": "PDK", "node": "N5"}
    mock_query_store.return_value = [mock_doc]
    
    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = lambda q, chunks, top_k: chunks
    mock_reranker_class.return_value = mock_reranker
    
    res = retrieve_pdk_rules("What is M3 pitch?", {"node": "n5"})
    
    assert res["logs"]["status"] == "success"
    assert len(res["chunks"]) == 1
    assert res["chunks"][0].page_content == "Metal pitch rule"
    
    mock_query_store.assert_called_once()
    called_filter = mock_query_store.call_args[1]["filter"]
    assert called_filter["category"] == "PDK"
    assert called_filter["node"] == "n5"

@patch("src.retrieval.pdk_retriever.query_vector_store")
def test_retrieve_pdk_rules_fallback_on_db_error(mock_query_store):
    mock_query_store.side_effect = RuntimeError("Connection refused")
    
    res = retrieve_pdk_rules("What is M3 pitch?", {"node": "N5"})
    
    assert res["logs"]["status"] == "failed"
    assert "Connection refused" in res["logs"]["error"]
    assert len(res["chunks"]) == 0
