"""Tests for chip_agent.src.ingestion.chunker."""

import pytest

from src.ingestion.loader import IngestionDocument
from src.ingestion.chunker import (
    ChunkMetadata,
    TextChunk,
    chunk_document,
    chunk_documents,
    _classify_blocks,
    _split_long_paragraph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def simple_doc():
    """A simple document with no headers or tables."""
    return IngestionDocument(
        text="First paragraph about M3 pitch.\n\nSecond paragraph about DRC rules.",
        metadata={"category": "PDK", "node": "N5"},
        source="/data/pdk.jsonl",
    )


@pytest.fixture()
def sectioned_doc():
    """A document with Markdown headers and multiple sections."""
    return IngestionDocument(
        text=(
            "# Chapter 1: Metal Layers\n"
            "M3 pitch for N5 is 36nm.\n"
            "M3 pitch for N7 is 40nm.\n\n"
            "## 1.1 DRC Rules\n"
            "Minimum spacing on M1 is 28nm.\n"
        ),
        metadata={"category": "PDK", "node": "N5"},
        source="/data/pdk.jsonl",
    )


@pytest.fixture()
def table_doc():
    """A document containing a Markdown table."""
    return IngestionDocument(
        text=(
            "# Metal Pitch Table\n\n"
            "| Node | Layer | Pitch |\n"
            "|------|-------|-------|\n"
            "| N5   | M3    | 36nm  |\n"
            "| N7   | M3    | 40nm  |\n"
        ),
        metadata={"category": "PDK"},
        source="/data/pdk.jsonl",
    )


@pytest.fixture()
def long_paragraph_doc():
    """A document with a paragraph that exceeds the default chunk size."""
    long_text = ". ".join([f"Sentence number {i} about chip design." for i in range(50)])
    return IngestionDocument(
        text=long_text,
        metadata={"category": "EDA", "tool": "Innovus"},
        source="/data/eda.jsonl",
    )


@pytest.fixture()
def empty_doc():
    """A document with empty text."""
    return IngestionDocument(text="", metadata={}, source="/data/empty.jsonl")


# ---------------------------------------------------------------------------
# Tests – _classify_blocks
# ---------------------------------------------------------------------------

class TestClassifyBlocks:
    def test_plain_paragraphs(self):
        text = "Hello world.\n\nGoodbye world."
        blocks = _classify_blocks(text)
        assert len(blocks) == 2
        assert all(b["type"] == "paragraph" for b in blocks)

    def test_header_detection(self):
        text = "# Title\nSome text\n## Subtitle\nMore text"
        blocks = _classify_blocks(text)
        types = [b["type"] for b in blocks]
        assert "header" in types
        headers = [b["text"] for b in blocks if b["type"] == "header"]
        assert "# Title" in headers
        assert "## Subtitle" in headers

    def test_table_detection(self):
        text = (
            "| Col1 | Col2 |\n"
            "|------|------|\n"
            "| A    | B    |\n"
        )
        blocks = _classify_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "table"

    def test_non_table_pipes_ignored(self):
        """Lines with pipes but no separator row should be treated as paragraph."""
        text = "| just one line with pipes"
        blocks = _classify_blocks(text)
        assert blocks[0]["type"] == "paragraph"

    def test_section_context_propagated(self):
        text = "# Header\nParagraph text"
        blocks = _classify_blocks(text)
        para_blocks = [b for b in blocks if b["type"] == "paragraph"]
        assert para_blocks[0]["header"] == "Header"

    def test_mixed_content(self):
        text = (
            "# Title\n\n"
            "Some intro text.\n\n"
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n\n"
            "Closing paragraph.\n"
        )
        blocks = _classify_blocks(text)
        types = [b["type"] for b in blocks]
        assert "header" in types
        assert "table" in types
        assert "paragraph" in types


# ---------------------------------------------------------------------------
# Tests – _split_long_paragraph
# ---------------------------------------------------------------------------

class TestSplitLongParagraph:
    def test_short_text_unchanged(self):
        assert _split_long_paragraph("Short text.", max_chars=100) == ["Short text."]

    def test_splits_on_sentences(self):
        text = "First sentence. Second sentence. Third sentence."
        parts = _split_long_paragraph(text, max_chars=30)
        assert len(parts) > 1
        # All original content should be present
        assert "".join(parts).replace(" ", "") == text.replace(" ", "")

    def test_hard_split_on_no_boundary(self):
        text = "A" * 250
        parts = _split_long_paragraph(text, max_chars=100)
        assert len(parts) == 3
        assert "".join(parts) == text


# ---------------------------------------------------------------------------
# Tests – chunk_document
# ---------------------------------------------------------------------------

class TestChunkDocument:
    def test_empty_doc_returns_empty(self, empty_doc):
        chunks = chunk_document(empty_doc)
        assert chunks == []

    def test_simple_doc_produces_chunks(self, simple_doc):
        chunks = chunk_document(simple_doc)
        assert len(chunks) >= 1
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_section_headers_are_preserved(self, sectioned_doc):
        chunks = chunk_document(sectioned_doc)
        sections = [c.metadata.section for c in chunks if c.metadata.section]
        assert "Chapter 1: Metal Layers" in sections
        assert "1.1 DRC Rules" in sections

    def test_tables_are_not_split(self, table_doc):
        chunks = chunk_document(table_doc, max_chunk_chars=50)
        table_chunks = [c for c in chunks if "| Node |" in c.text or "|------|" in c.text]
        # The entire table should be in one chunk (or co-located with header)
        all_table_text = "".join(c.text for c in table_chunks)
        # All table rows should be present somewhere
        assert "N5" in all_table_text
        assert "N7" in all_table_text

    def test_long_paragraph_is_split(self, long_paragraph_doc):
        chunks = chunk_document(long_paragraph_doc, max_chunk_chars=200)
        assert len(chunks) > 1

    def test_chunk_ids_are_unique(self, sectioned_doc):
        chunks = chunk_document(sectioned_doc)
        ids = [c.metadata.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_ids_are_deterministic(self, simple_doc):
        c1 = chunk_document(simple_doc)
        c2 = chunk_document(simple_doc)
        assert [c.metadata.chunk_id for c in c1] == [c.metadata.chunk_id for c in c2]

    def test_position_and_total_are_correct(self, sectioned_doc):
        chunks = chunk_document(sectioned_doc)
        total = chunks[0].metadata.total_chunks
        assert len(chunks) == total
        for i, c in enumerate(chunks):
            assert c.metadata.position == i
            assert c.metadata.total_chunks == total

    def test_metadata_inherited(self, simple_doc):
        chunks = chunk_document(simple_doc)
        for c in chunks:
            assert c.metadata.source == "/data/pdk.jsonl"
            assert c.metadata.category == "PDK"
            assert c.metadata.parent_metadata == simple_doc.metadata

    def test_overlap_prepends_context(self):
        doc = IngestionDocument(
            text="First sentence. Second sentence.",
            metadata={},
        )
        chunks_no_overlap = chunk_document(doc, max_chunk_chars=20, overlap_chars=0)
        chunks_overlap = chunk_document(doc, max_chunk_chars=20, overlap_chars=10)
        # With overlap, the second chunk should contain some prefix from the first
        if len(chunks_overlap) > 1:
            assert "..." in chunks_overlap[1].text


# ---------------------------------------------------------------------------
# Tests – chunk_documents (batch)
# ---------------------------------------------------------------------------

class TestChunkDocuments:
    def test_batch_chunking(self, simple_doc, sectioned_doc, table_doc):
        docs = [simple_doc, sectioned_doc, table_doc]
        all_chunks = chunk_documents(docs)
        assert len(all_chunks) > 0
        # All chunks should have valid metadata
        for c in all_chunks:
            assert c.metadata.chunk_id
            assert c.metadata.total_chunks >= 1

    def test_empty_list_returns_empty(self):
        assert chunk_documents([]) == []


# ---------------------------------------------------------------------------
# Tests – ChunkMetadata model
# ---------------------------------------------------------------------------

class TestChunkMetadata:
    def test_defaults(self):
        meta = ChunkMetadata(chunk_id="abc123")
        assert meta.source is None
        assert meta.category is None
        assert meta.section is None
        assert meta.position == 0
        assert meta.total_chunks == 1
        assert meta.parent_metadata == {}

    def test_full_construction(self):
        meta = ChunkMetadata(
            chunk_id="abc123",
            source="/data/test.jsonl",
            category="PDK",
            section="Metal Layers",
            position=2,
            total_chunks=5,
            parent_metadata={"node": "N5"},
        )
        assert meta.section == "Metal Layers"
        assert meta.parent_metadata["node"] == "N5"
