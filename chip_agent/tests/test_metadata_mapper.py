"""Tests for chip_agent.src.ingestion.metadata_mapper."""

import pytest
from datetime import datetime, timezone

from src.ingestion.loader import IngestionDocument
from src.ingestion.chunker import ChunkMetadata, TextChunk, chunk_document
from src.ingestion.metadata_mapper import (
    ChunkIndexMetadata,
    _generate_doc_id,
    _normalize_category,
    _normalize_node,
    _normalize_project_id,
    _normalize_tool,
    map_chunks,
    merge_metadata,
    normalize_metadata_fields,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def pdk_doc():
    """A PDK document with full metadata."""
    return IngestionDocument(
        text="The M3 metal pitch for N5 process node is 36nm.",
        metadata={
            "category": "PDK",
            "node": "N5",
            "tool": "Innovus",
            "project_id": "Proj_A",
            "section": "M3 Pitch",
        },
        source="/data/pdk_rules.jsonl",
    )


@pytest.fixture()
def eda_doc():
    """An EDA document with minimal metadata."""
    return IngestionDocument(
        text="Innovus command floorPlan configures floorplan boundaries.",
        metadata={"category": "EDA", "tool": "Innovus"},
        source="/data/eda_manuals.jsonl",
    )


@pytest.fixture()
def project_doc():
    """A Project_Doc document."""
    return IngestionDocument(
        text="Project Proj_A design specification targets N5 with Innovus.",
        metadata={
            "category": "Project_Doc",
            "project_id": "Proj_A",
            "node": "N5",
            "tool": "Innovus",
        },
        source="/data/project_docs.jsonl",
    )


@pytest.fixture()
def minimal_doc():
    """A document with no metadata fields at all."""
    return IngestionDocument(
        text="Some generic text.",
        metadata={},
        source="/data/generic.jsonl",
    )


@pytest.fixture()
def pdk_chunks(pdk_doc):
    """Chunks from the PDK document."""
    return chunk_document(pdk_doc, max_chunk_chars=200)


@pytest.fixture()
def single_chunk():
    """A single TextChunk with known metadata."""
    meta = ChunkMetadata(
        chunk_id="abc123",
        source="/data/pdk.jsonl",
        category="PDK",
        section="Metal Layers",
        position=0,
        total_chunks=1,
        parent_metadata={"category": "PDK", "node": "N5", "tool": "Innovus"},
    )
    return TextChunk(text="M3 pitch is 36nm.", metadata=meta)


# ---------------------------------------------------------------------------
# Tests – _normalize_category
# ---------------------------------------------------------------------------


class TestNormalizeCategory:
    def test_canonical_values_unchanged(self):
        assert _normalize_category("PDK") == "PDK"
        assert _normalize_category("EDA") == "EDA"
        assert _normalize_category("Project_Doc") == "Project_Doc"
        assert _normalize_category("Literature") == "Literature"
        assert _normalize_category("Platform_Flow") == "Platform_Flow"
        assert _normalize_category("StdCell") == "StdCell"
        assert _normalize_category("SRAM") == "SRAM"

    def test_lowercase_alias(self):
        assert _normalize_category("pdk") == "PDK"
        assert _normalize_category("eda") == "EDA"
        assert _normalize_category("general") == "Literature"

    def test_synonym_aliases(self):
        assert _normalize_category("process") == "PDK"
        assert _normalize_category("foundry_doc") == "PDK"
        assert _normalize_category("tool") == "EDA"
        assert _normalize_category("project") == "Project_Doc"
        assert _normalize_category("doc") == "Project_Doc"
        assert _normalize_category("project_doc") == "Project_Doc"
        assert _normalize_category("liberty") == "StdCell"
        assert _normalize_category("memory") == "SRAM"
        assert _normalize_category("checklist_template") == "Platform_Flow"
        assert _normalize_category("checklist_result") == "Project_Doc"
        assert _normalize_category("script") == "Script"

    def test_none_returns_none(self):
        assert _normalize_category(None) is None

    def test_whitespace_stripped(self):
        assert _normalize_category("  PDK  ") == "PDK"
        assert _normalize_category("  eda  ") == "EDA"


# ---------------------------------------------------------------------------
# Tests – _normalize_node
# ---------------------------------------------------------------------------


class TestNormalizeNode:
    def test_canonical_values(self):
        assert _normalize_node("N5") == "N5"
        assert _normalize_node("N7") == "N7"

    def test_alternate_formats(self):
        assert _normalize_node("5nm") == "N5"
        assert _normalize_node("7nm") == "N7"
        assert _normalize_node("5") == "N5"
        assert _normalize_node("7") == "N7"

    def test_case_insensitive(self):
        assert _normalize_node("n5") == "N5"
        assert _normalize_node("N5") == "N5"

    def test_none_returns_none(self):
        assert _normalize_node(None) is None

    def test_unknown_kept_as_is(self):
        assert _normalize_node("N3") == "N3"


# ---------------------------------------------------------------------------
# Tests – _normalize_tool
# ---------------------------------------------------------------------------


class TestNormalizeTool:
    def test_canonical_values(self):
        assert _normalize_tool("Innovus") == "Innovus"
        assert _normalize_tool("ICC2") == "ICC2"
        assert _normalize_tool("Calibre") == "Calibre"
        assert _normalize_tool("PrimeTime") == "PrimeTime"

    def test_synonyms(self):
        assert _normalize_tool("encounter") == "Innovus"
        assert _normalize_tool("icc") == "ICC2"
        assert _normalize_tool("ic compiler") == "ICC2"
        assert _normalize_tool("pt") == "PrimeTime"

    def test_case_insensitive(self):
        assert _normalize_tool("innovus") == "Innovus"
        assert _normalize_tool("INNOVUS") == "Innovus"

    def test_none_returns_none(self):
        assert _normalize_tool(None) is None

    def test_unknown_capitalized(self):
        assert _normalize_tool("synopsys") == "Synopsys"


# ---------------------------------------------------------------------------
# Tests – _normalize_project_id
# ---------------------------------------------------------------------------


class TestNormalizeProjectId:
    def test_canonical_values(self):
        assert _normalize_project_id("Proj_A") == "Proj_A"
        assert _normalize_project_id("Proj_B") == "Proj_B"

    def test_synonyms(self):
        assert _normalize_project_id("projecta") == "Proj_A"
        assert _normalize_project_id("projb") == "Proj_B"
        assert _normalize_project_id("proj-a") == "Proj_A"
        assert _normalize_project_id("proj_b") == "Proj_B"

    def test_none_returns_none(self):
        assert _normalize_project_id(None) is None

    def test_unknown_kept_as_is(self):
        assert _normalize_project_id("Proj_C") == "Proj_C"


# ---------------------------------------------------------------------------
# Tests – _generate_doc_id
# ---------------------------------------------------------------------------


class TestGenerateDocId:
    def test_deterministic(self):
        id1 = _generate_doc_id("/data/pdk.jsonl", "Some text")
        id2 = _generate_doc_id("/data/pdk.jsonl", "Some text")
        assert id1 == id2

    def test_different_source_different_id(self):
        id1 = _generate_doc_id("/data/a.jsonl", "Same text")
        id2 = _generate_doc_id("/data/b.jsonl", "Same text")
        assert id1 != id2

    def test_different_text_different_id(self):
        id1 = _generate_doc_id("/data/a.jsonl", "Text A")
        id2 = _generate_doc_id("/data/a.jsonl", "Text B")
        assert id1 != id2

    def test_none_source_handled(self):
        doc_id = _generate_doc_id(None, "Some text")
        assert isinstance(doc_id, str)
        assert len(doc_id) == 16

    def test_returns_16_hex_chars(self):
        doc_id = _generate_doc_id("/data/test.jsonl", "Hello world")
        assert len(doc_id) == 16
        int(doc_id, 16)  # Should not raise


# ---------------------------------------------------------------------------
# Tests – normalize_metadata_fields
# ---------------------------------------------------------------------------


class TestNormalizeMetadataFields:
    def test_normalizes_all_fields(self):
        meta = {
            "category": "pdk",
            "node": "n5",
            "tool": "innovus",
            "project_id": "proja",
        }
        result = normalize_metadata_fields(meta)
        assert result["category"] == "PDK"
        assert result["node"] == "N5"
        assert result["tool"] == "Innovus"
        assert result["project_id"] == "Proj_A"

    def test_modifies_in_place(self):
        meta = {"category": "eda"}
        result = normalize_metadata_fields(meta)
        assert result is meta  # Same object

    def test_missing_fields_left_untouched(self):
        meta = {"category": "PDK"}
        result = normalize_metadata_fields(meta)
        assert "node" not in result
        assert "tool" not in result

    def test_empty_dict(self):
        assert normalize_metadata_fields({}) == {}

    def test_none_values_preserved(self):
        meta = {"category": None, "node": None}
        result = normalize_metadata_fields(meta)
        assert result["category"] is None
        assert result["node"] is None


# ---------------------------------------------------------------------------
# Tests – merge_metadata
# ---------------------------------------------------------------------------


class TestMergeMetadata:
    def test_full_metadata_from_doc(self, pdk_doc, single_chunk):
        result = merge_metadata(single_chunk, pdk_doc)
        assert isinstance(result, ChunkIndexMetadata)
        assert result.category == "PDK"
        assert result.node == "N5"
        assert result.tool == "Innovus"
        assert result.project_id == "Proj_A"
        assert result.source == "/data/pdk.jsonl"
        assert result.section == "Metal Layers"
        assert result.chunk_id == "abc123"

    def test_doc_id_is_set(self, pdk_doc, single_chunk):
        result = merge_metadata(single_chunk, pdk_doc)
        assert result.doc_id
        assert len(result.doc_id) == 16

    def test_updated_at_is_iso_utc(self, pdk_doc, single_chunk):
        result = merge_metadata(single_chunk, pdk_doc)
        # Should be parseable as ISO-8601
        dt = datetime.fromisoformat(result.updated_at)
        assert dt.tzinfo is not None

    def test_chunk_id_preserved(self, pdk_doc, single_chunk):
        result = merge_metadata(single_chunk, pdk_doc)
        assert result.chunk_id == "abc123"

    def test_section_from_chunk(self, pdk_doc, single_chunk):
        result = merge_metadata(single_chunk, pdk_doc)
        assert result.section == "Metal Layers"

    def test_fallback_to_parent_metadata(self, single_chunk):
        """When doc is None, parent_metadata from the chunk is used."""
        result = merge_metadata(single_chunk, doc=None)
        assert result.category == "PDK"
        assert result.node == "N5"
        assert result.tool == "Innovus"

    def test_minimal_metadata(self, minimal_doc):
        meta = ChunkMetadata(
            chunk_id="min001",
            source="/data/generic.jsonl",
            parent_metadata={},
        )
        chunk = TextChunk(text="Some generic text.", metadata=meta)
        result = merge_metadata(chunk, minimal_doc)
        assert result.category is None
        assert result.node is None
        assert result.tool is None
        assert result.project_id is None
        assert result.page is None

    def test_page_from_metadata(self):
        doc = IngestionDocument(
            text="Page 5 content.",
            metadata={"category": "PDK", "page": 5},
            source="/data/pdk.jsonl",
        )
        meta = ChunkMetadata(
            chunk_id="page001",
            source="/data/pdk.jsonl",
            parent_metadata=doc.metadata,
        )
        chunk = TextChunk(text="Page 5 content.", metadata=meta)
        result = merge_metadata(chunk, doc)
        assert result.page == 5

    def test_page_string_converted_to_int(self):
        doc = IngestionDocument(
            text="Page content.",
            metadata={"category": "PDK", "page": "10"},
            source="/data/pdk.jsonl",
        )
        meta = ChunkMetadata(
            chunk_id="page002",
            source="/data/pdk.jsonl",
            parent_metadata=doc.metadata,
        )
        chunk = TextChunk(text="Page content.", metadata=meta)
        result = merge_metadata(chunk, doc)
        assert result.page == 10

    def test_page_invalid_string_becomes_none(self):
        doc = IngestionDocument(
            text="Page content.",
            metadata={"category": "PDK", "page": "not_a_number"},
            source="/data/pdk.jsonl",
        )
        meta = ChunkMetadata(
            chunk_id="page003",
            source="/data/pdk.jsonl",
            parent_metadata=doc.metadata,
        )
        chunk = TextChunk(text="Page content.", metadata=meta)
        result = merge_metadata(chunk, doc)
        assert result.page is None

    def test_normalization_applied(self):
        """Metadata with lowercase aliases should be normalised."""
        doc = IngestionDocument(
            text="Test text.",
            metadata={"category": "pdk", "node": "n5", "tool": "innovus"},
            source="/data/test.jsonl",
        )
        meta = ChunkMetadata(
            chunk_id="norm001",
            source="/data/test.jsonl",
            parent_metadata=doc.metadata,
        )
        chunk = TextChunk(text="Test text.", metadata=meta)
        result = merge_metadata(chunk, doc)
        assert result.category == "PDK"
        assert result.node == "N5"
        assert result.tool == "Innovus"


# ---------------------------------------------------------------------------
# Tests – map_chunks (batch)
# ---------------------------------------------------------------------------


class TestMapChunks:
    def test_maps_multiple_chunks(self, pdk_doc, pdk_chunks):
        results = map_chunks(pdk_chunks, pdk_doc)
        assert len(results) == len(pdk_chunks)
        assert all(isinstance(r, ChunkIndexMetadata) for r in results)

    def test_all_chunks_share_same_doc_id(self, pdk_doc, pdk_chunks):
        results = map_chunks(pdk_chunks, pdk_doc)
        doc_ids = {r.doc_id for r in results}
        assert len(doc_ids) == 1

    def test_chunk_ids_are_unique(self, pdk_doc, pdk_chunks):
        results = map_chunks(pdk_chunks, pdk_doc)
        chunk_ids = [r.chunk_id for r in results]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_empty_list(self):
        results = map_chunks([])
        assert results == []

    def test_all_required_fields_present(self, pdk_doc, pdk_chunks):
        """Every ChunkIndexMetadata should have all unified fields."""
        results = map_chunks(pdk_chunks, pdk_doc)
        for r in results:
            # These fields must always be present (even if None)
            assert r.doc_id is not None
            assert r.chunk_id is not None
            assert r.updated_at is not None
            # category, node, tool, project_id, source, section, page may be None
            _ = r.category
            _ = r.node
            _ = r.tool
            _ = r.project_id
            _ = r.source
            _ = r.section
            _ = r.page

    def test_doc_none_uses_parent_metadata(self, pdk_chunks):
        """When doc is None, chunks use their own parent_metadata."""
        results = map_chunks(pdk_chunks, doc=None)
        assert len(results) == len(pdk_chunks)
        # parent_metadata on pdk_chunks has category=PDK
        for r in results:
            assert r.category == "PDK"

    def test_fields_match_seed_data_pattern(self, project_doc):
        """Verify the output matches the seed data structure."""
        chunks = chunk_document(project_doc, max_chunk_chars=500)
        results = map_chunks(chunks, project_doc)
        r = results[0]
        assert r.category == "Project_Doc"
        assert r.node == "N5"
        assert r.tool == "Innovus"
        assert r.project_id == "Proj_A"


# ---------------------------------------------------------------------------
# Tests – ChunkIndexMetadata model
# ---------------------------------------------------------------------------


class TestChunkIndexMetadata:
    def test_construction_with_all_fields(self):
        meta = ChunkIndexMetadata(
            doc_id="doc123",
            chunk_id="chunk456",
            category="PDK",
            node="N5",
            tool="Innovus",
            project_id="Proj_A",
            source="/data/pdk.jsonl",
            section="M3 Pitch",
            page=3,
        )
        assert meta.doc_id == "doc123"
        assert meta.chunk_id == "chunk456"
        assert meta.category == "PDK"
        assert meta.node == "N5"
        assert meta.tool == "Innovus"
        assert meta.project_id == "Proj_A"
        assert meta.source == "/data/pdk.jsonl"
        assert meta.section == "M3 Pitch"
        assert meta.page == 3
        assert meta.updated_at  # auto-generated

    def test_optional_fields_default_to_none(self):
        meta = ChunkIndexMetadata(doc_id="d1", chunk_id="c1")
        assert meta.category is None
        assert meta.node is None
        assert meta.tool is None
        assert meta.project_id is None
        assert meta.source is None
        assert meta.section is None
        assert meta.page is None

    def test_updated_at_auto_generated(self):
        meta = ChunkIndexMetadata(doc_id="d1", chunk_id="c1")
        dt = datetime.fromisoformat(meta.updated_at)
        assert dt.tzinfo is not None
        # Should be very close to now (within 5 seconds)
        now = datetime.now(timezone.utc)
        diff = abs((now - dt).total_seconds())
        assert diff < 5
