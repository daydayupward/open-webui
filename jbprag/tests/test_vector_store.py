import pytest
from unittest.mock import patch, MagicMock
from src.vector_store import get_vector_store
from langchain_core.embeddings import FakeEmbeddings

@patch("src.vector_store.PGVector")
@pytest.mark.anyio
async def test_get_vector_store(mock_pgvector):
    mock_store = MagicMock()
    mock_store.collection_name = "test_col"
    mock_pgvector.return_value = mock_store

    embeddings = FakeEmbeddings(size=1536)
    store = get_vector_store(
        connection_string="postgresql+psycopg://user:pass@localhost:5432/db",
        collection_name="test_col",
        embeddings=embeddings
    )
    
    mock_pgvector.assert_called_once_with(
        embeddings=embeddings,
        collection_name="test_col",
        connection="postgresql+psycopg://user:pass@localhost:5432/db",
        use_jsonb=True
    )
    assert store.collection_name == "test_col"
