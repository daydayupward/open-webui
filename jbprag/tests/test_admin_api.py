import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
import src.admin_db as admin_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Use temporary sqlite database for tests
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_admin.db")
    
    with patch("src.admin_db.DB_PATH", temp_db_path):
        admin_db.init_db()
        yield
        
    try:
        os.remove(temp_db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass

@pytest.mark.anyio
async def test_get_and_update_config():
    # GET initial config
    res = client.get("/admin/config")
    assert res.status_code == 200
    data = res.json()
    assert data["pdk_rules_collection"] == "pdk_rules"
    assert data["default_header_margin"] == "50"
    
    # POST updated config
    update_res = client.post("/admin/config", json={
        "default_header_margin": "80",
        "pdk_rules_collection": "pdk_rules_v2"
    })
    assert update_res.status_code == 200
    
    # Verify updated config
    res_updated = client.get("/admin/config")
    data_updated = res_updated.json()
    assert data_updated["default_header_margin"] == "80"
    assert data_updated["pdk_rules_collection"] == "pdk_rules_v2"

@patch("src.admin_router.get_llm")
@pytest.mark.anyio
async def test_ingest_precheck(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content='{"category": "PDK", "vendor": "TSMC"}'))
    mock_get_llm.return_value = mock_llm
    
    # Send a dummy file for precheck
    file_data = {"file": ("test.pdf", b"%PDF-1.4 dummy contents", "application/pdf")}
    res = client.post("/admin/ingest/precheck", files=file_data)
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "PDK"
    assert data["vendor"] == "TSMC"

@patch("src.admin_router.clean_pdf_file")
@patch("src.admin_router.chunk_document")
@patch("src.admin_router.index_chunks")
@pytest.mark.anyio
async def test_ingest_and_documents_catalog(mock_index, mock_chunk, mock_clean):
    mock_clean.return_value = True
    mock_chunk.return_value = []
    mock_index.return_value = {"inserted": 0}
    
    # 1. Ingest a document
    file_data = {"file": ("drc_rules.pdf", b"%PDF-1.4 dummy", "application/pdf")}
    payload = {
        "category": "PDK",
        "node": "N5",
        "vendor": "TSMC",
        "header_margin": "75"
    }
    
    res = client.post("/admin/ingest", files=file_data, data=payload)
    assert res.status_code == 200
    doc_id = res.json()["doc_id"]
    assert doc_id is not None
    
    # 2. Get list of documents
    res_docs = client.get("/admin/documents")
    assert res_docs.status_code == 200
    docs = res_docs.json()
    assert len(docs) == 1
    assert docs[0]["doc_id"] == doc_id
    assert docs[0]["filename"] == "drc_rules.pdf"
    assert docs[0]["category"] == "PDK"
    assert docs[0]["node"] == "N5"

@patch("src.admin_router.delete_by_doc_id")
@pytest.mark.anyio
async def test_delete_document(mock_delete):
    # Save a dummy doc
    doc_id = "testdoc123"
    admin_db.save_document({
        "doc_id": doc_id,
        "filename": "dummy.pdf",
        "filepath": "dummy_path.pdf",
        "category": "PDK",
        "status": "success"
    })
    
    # Delete doc
    res = client.delete(f"/admin/documents/{doc_id}")
    assert res.status_code == 200
    
    # Verify deleted
    res_docs = client.get("/admin/documents")
    assert len(res_docs.json()) == 0

@patch("src.admin_router.get_all_vector_collections")
@pytest.mark.anyio
async def test_indexes_and_switch(mock_get_cols):
    mock_get_cols.return_value = ["pdk_rules", "pdk_rules_v2", "eda_manuals"]
    
    # 1. GET current active indexes
    res = client.get("/admin/indexes")
    assert res.status_code == 200
    data = res.json()
    assert data["active"]["PDK"] == "pdk_rules"
    assert "pdk_rules_v2" in data["collections"]
    
    # 2. Switch PDK active collection
    switch_res = client.post("/admin/indexes/switch", json={
        "category": "PDK",
        "collection": "pdk_rules_v2"
    })
    assert switch_res.status_code == 200
    
    # 3. Verify switched collection
    res_updated = client.get("/admin/indexes")
    assert res_updated.json()["active"]["PDK"] == "pdk_rules_v2"

@patch("src.admin_router.get_embeddings")
@patch("src.vector_store.aquery_vector_store")
@patch("src.retrieval.reranker.QwenRerankerClient")
@pytest.mark.anyio
async def test_indexes_test(mock_reranker_class, mock_query, mock_emb):
    # Mock query returning doc
    mock_doc = MagicMock()
    mock_doc.page_content = "M1 spacing is 36nm."
    mock_doc.metadata = {"name": "pdk_rules.pdf"}
    mock_query.return_value = [mock_doc]
    
    # Mock reranker client
    mock_reranker = MagicMock()
    mock_chunk = MagicMock()
    mock_chunk.page_content = "M1 spacing is 36nm."
    mock_chunk.metadata = {"name": "pdk_rules.pdf", "relevance_score": 0.95}
    mock_reranker.rerank.return_value = [mock_chunk]
    mock_reranker_class.return_value = mock_reranker
    
    res = client.post("/admin/indexes/test", json={
        "query": "M1 spacing",
        "collection": "pdk_rules",
        "k": 1
    })
    
    assert res.status_code == 200
    data = res.json()
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["page_content"] == "M1 spacing is 36nm."
    assert data["chunks"][0]["score"] == 0.95

@pytest.mark.anyio
async def test_traces_and_evaluations():
    # Save a test trace
    admin_db.save_trace(
        trace_id="t1",
        query="M1 pitch",
        rewritten_query="M1 layer spacing pitch",
        chunks=[{"page_content": "M1 pitch is 36nm", "metadata": {"source": "pdf"}}],
        answer="The metal pitch is 36nm."
    )
    
    # Save a test evaluation
    admin_db.save_evaluation("e1", {"faithfulness": 0.9, "answer_relevance": 0.85})
    
    # GET traces
    res_traces = client.get("/admin/traces")
    assert res_traces.status_code == 200
    traces_data = res_traces.json()
    assert len(traces_data) == 1
    assert traces_data[0]["id"] == "t1"
    assert traces_data[0]["query"] == "M1 pitch"
    
    # GET evaluations
    res_evals = client.get("/admin/evaluation")
    assert res_evals.status_code == 200
    evals_data = res_evals.json()
    assert len(evals_data) == 1
    assert evals_data[0]["id"] == "e1"
    assert evals_data[0]["metrics"]["faithfulness"] == 0.9
