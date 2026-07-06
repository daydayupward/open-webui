"""Tests for the ingestion indexer module."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.ingestion.chunker import ChunkMetadata, TextChunk
from src.ingestion.indexer import (
    _build_document,
    _deduplicate_chunks,
    delete_by_doc_id,
    get_indexed_chunk_ids,
    index_chunks,
)
from src.ingestion.metadata_mapper import ChunkIndexMetadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_chunk(chunk_id: str = "abc123", text: str = "test content") -> TextChunk:
    """Create a TextChunk with minimal metadata for testing."""
    return TextChunk(
        text=text,
        metadata=ChunkMetadata(
            chunk_id=chunk_id,
            source="/test/source.jsonl",
            category="PDK",
            section="Test Section",
            position=0,
            total_chunks=1,
            parent_metadata={"category": "PDK"},
        ),
    )


def _make_metadata(chunk_id: str = "abc123") -> ChunkIndexMetadata:
    """Create a ChunkIndexMetadata for testing."""
    return ChunkIndexMetadata(
        doc_id="doc123",
        chunk_id=chunk_id,
        category="PDK",
        node="N5",
        tool="Innovus",
        project_id="Proj_A",
        source="/test/source.jsonl",
        section="Test Section",
        page=None,
        updated_at="2024-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# Tests for _build_document
# ---------------------------------------------------------------------------


class TestBuildDocument:
    def test_build_document_basic(self):
        chunk = _make_chunk()
        meta = _make_metadata()

        doc = _build_document(chunk, meta)

        assert isinstance(doc, Document)
        assert doc.page_content == "test content"
        assert doc.metadata["chunk_id"] == "abc123"
        assert doc.metadata["doc_id"] == "doc123"
        assert doc.metadata["category"] == "PDK"
        assert doc.metadata["node"] == "N5"
        assert doc.metadata["tool"] == "Innovus"
        assert doc.metadata["project_id"] == "Proj_A"
        assert doc.metadata["source"] == "/test/source.jsonl"
        assert doc.metadata["section"] == "Test Section"
        assert doc.metadata["page"] is None
        assert doc.metadata["updated_at"] == "2024-01-01T00:00:00+00:00"

    def test_build_document_with_none_fields(self):
        chunk = _make_chunk()
        meta = ChunkIndexMetadata(
            doc_id="doc456",
            chunk_id="def456",
            category=None,
            node=None,
            tool=None,
            project_id=None,
            source=None,
            section=None,
            page=None,
        )

        doc = _build_document(chunk, meta)

        assert doc.metadata["chunk_id"] == "def456"
        assert doc.metadata["category"] is None
        assert doc.metadata["node"] is None
        assert doc.metadata["source"] is None


# ---------------------------------------------------------------------------
# Tests for _deduplicate_chunks
# ---------------------------------------------------------------------------


class TestDeduplicateChunks:
    def test_no_duplicates(self):
        chunks = [_make_chunk("id1"), _make_chunk("id2"), _make_chunk("id3")]
        metas = [_make_metadata("id1"), _make_metadata("id2"), _make_metadata("id3")]

        deduped_chunks, deduped_metas = _deduplicate_chunks(chunks, metas)

        assert len(deduped_chunks) == 3
        assert len(deduped_metas) == 3
        assert [m.chunk_id for m in deduped_metas] == ["id1", "id2", "id3"]

    def test_with_duplicates_keeps_last(self):
        chunks = [
            _make_chunk("id1", "first version"),
            _make_chunk("id2", "other content"),
            _make_chunk("id1", "updated version"),
        ]
        metas = [_make_metadata("id1"), _make_metadata("id2"), _make_metadata("id1")]

        deduped_chunks, deduped_metas = _deduplicate_chunks(chunks, metas)

        assert len(deduped_chunks) == 2
        # The last occurrence of id1 should be kept
        id1_chunk = next(c for c, m in zip(deduped_chunks, deduped_metas) if m.chunk_id == "id1")
        assert id1_chunk.text == "updated version"

    def test_empty_input(self):
        deduped_chunks, deduped_metas = _deduplicate_chunks([], [])
        assert deduped_chunks == []
        assert deduped_metas == []

    def test_all_same_id(self):
        chunks = [_make_chunk("id1", "v1"), _make_chunk("id1", "v2"), _make_chunk("id1", "v3")]
        metas = [_make_metadata("id1"), _make_metadata("id1"), _make_metadata("id1")]

        deduped_chunks, deduped_metas = _deduplicate_chunks(chunks, metas)

        assert len(deduped_chunks) == 1
        assert deduped_chunks[0].text == "v3"


# ---------------------------------------------------------------------------
# Tests for index_chunks
# ---------------------------------------------------------------------------


class TestIndexChunks:
    @patch("src.ingestion.indexer.get_vector_store")
    @patch("src.ingestion.indexer.map_chunks")
    def test_index_single_chunk(self, mock_map, mock_get_store):
        chunk = _make_chunk()
        meta = _make_metadata()
        mock_map.return_value = [meta]

        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        stats = index_chunks(
            chunks=[chunk],
            connection_string="postgresql://test",
            collection_name="test_col",
            embeddings=MagicMock(),
        )

        assert stats["total_input"] == 1
        assert stats["after_dedup"] == 1
        assert stats["indexed"] == 1
        assert stats["batches"] == 1
        mock_store.add_documents.assert_called_once()
        call_args = mock_store.add_documents.call_args
        assert call_args[1]["ids"] == ["abc123"]

    @patch("src.ingestion.indexer.get_vector_store")
    @patch("src.ingestion.indexer.map_chunks")
    def test_index_multiple_chunks(self, mock_map, mock_get_store):
        chunks = [_make_chunk(f"id{i}") for i in range(5)]
        metas = [_make_metadata(f"id{i}") for i in range(5)]
        mock_map.return_value = metas

        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        stats = index_chunks(
            chunks=chunks,
            connection_string="postgresql://test",
            collection_name="test_col",
            embeddings=MagicMock(),
            batch_size=2,
        )

        assert stats["total_input"] == 5
        assert stats["after_dedup"] == 5
        assert stats["indexed"] == 5
        assert stats["batches"] == 3  # 2 + 2 + 1
        assert mock_store.add_documents.call_count == 3

    @patch("src.ingestion.indexer.get_vector_store")
    @patch("src.ingestion.indexer.map_chunks")
    def test_index_empty_chunks(self, mock_map, mock_get_store):
        stats = index_chunks(
            chunks=[],
            connection_string="postgresql://test",
            collection_name="test_col",
            embeddings=MagicMock(),
        )

        assert stats["total_input"] == 0
        assert stats["after_dedup"] == 0
        assert stats["indexed"] == 0
        assert stats["batches"] == 0
        mock_get_store.assert_not_called()

    @patch("src.ingestion.indexer.get_vector_store")
    @patch("src.ingestion.indexer.map_chunks")
    def test_index_with_duplicates_in_batch(self, mock_map, mock_get_store):
        chunks = [
            _make_chunk("id1", "first"),
            _make_chunk("id2", "other"),
            _make_chunk("id1", "updated"),
        ]
        metas = [_make_metadata("id1"), _make_metadata("id2"), _make_metadata("id1")]
        mock_map.return_value = metas

        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        stats = index_chunks(
            chunks=chunks,
            connection_string="postgresql://test",
            collection_name="test_col",
            embeddings=MagicMock(),
        )

        assert stats["total_input"] == 3
        assert stats["after_dedup"] == 2
        assert stats["indexed"] == 2

    @patch("src.ingestion.indexer.get_vector_store")
    @patch("src.ingestion.indexer.map_chunks")
    def test_index_raises_on_store_error(self, mock_map, mock_get_store):
        chunk = _make_chunk()
        meta = _make_metadata()
        mock_map.return_value = [meta]

        mock_store = MagicMock()
        mock_store.add_documents.side_effect = Exception("DB connection failed")
        mock_get_store.return_value = mock_store

        with pytest.raises(RuntimeError, match="Indexing failed at batch 1"):
            index_chunks(
                chunks=[chunk],
                connection_string="postgresql://test",
                collection_name="test_col",
                embeddings=MagicMock(),
            )


# ---------------------------------------------------------------------------
# Tests for delete_by_doc_id
# ---------------------------------------------------------------------------


class TestDeleteByDocId:
    @patch("src.ingestion.indexer.get_vector_store")
    def test_delete_success(self, mock_get_store):
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        result = delete_by_doc_id(
            doc_id="doc123",
            connection_string="postgresql://test",
            collection_name="test_col",
            embeddings=MagicMock(),
        )

        mock_store.delete.assert_called_once_with(filter={"doc_id": "doc123"})
        assert result == 0

    @patch("src.ingestion.indexer.get_vector_store")
    def test_delete_raises_on_error(self, mock_get_store):
        mock_store = MagicMock()
        mock_store.delete.side_effect = Exception("Delete failed")
        mock_get_store.return_value = mock_store

        with pytest.raises(RuntimeError, match="Deletion failed"):
            delete_by_doc_id(
                doc_id="doc123",
                connection_string="postgresql://test",
                collection_name="test_col",
                embeddings=MagicMock(),
            )


# ---------------------------------------------------------------------------
# Tests for get_indexed_chunk_ids
# ---------------------------------------------------------------------------


class TestGetIndexedChunkIds:
    @patch("sqlalchemy.create_engine")
    def test_returns_chunk_ids(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # Mocking result rows (tuples)
        mock_conn.execute.return_value = [("id1",), ("id2",)]
        mock_create_engine.return_value = mock_engine

        chunk_ids = get_indexed_chunk_ids(
            connection_string="postgresql://test",
            collection_name="test_col",
            embeddings=MagicMock(),
        )

        assert chunk_ids == ["id1", "id2"]
        mock_conn.execute.assert_called_once()
        
    @patch("sqlalchemy.create_engine")
    def test_returns_empty_on_no_results(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        mock_conn.execute.return_value = []
        mock_create_engine.return_value = mock_engine

        chunk_ids = get_indexed_chunk_ids(
            connection_string="postgresql://test",
            collection_name="test_col",
            embeddings=MagicMock(),
        )

        assert chunk_ids == []

    @patch("sqlalchemy.create_engine")
    def test_filters_by_doc_id(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        mock_conn.execute.return_value = []
        mock_create_engine.return_value = mock_engine

        get_indexed_chunk_ids(
            connection_string="postgresql://test",
            collection_name="test_col",
            embeddings=MagicMock(),
            doc_id="specific_doc",
        )

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        params = call_args[1]
        assert params["collection"] == "test_col"
        assert params["doc_id"] == "specific_doc"

    @patch("sqlalchemy.create_engine")
    def test_raises_on_error(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.side_effect = Exception("Query failed")
        mock_create_engine.return_value = mock_engine

        with pytest.raises(RuntimeError, match="Failed to query indexed chunk_ids"):
            get_indexed_chunk_ids(
                connection_string="postgresql://test",
                collection_name="test_col",
                embeddings=MagicMock(),
            )
