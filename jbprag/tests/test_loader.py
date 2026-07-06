"""Tests for jbprag.src.ingestion.loader."""

import json
import os
import tempfile

import pytest

from src.ingestion.loader import (
    IngestionDocument,
    load_all_documents,
    load_eda_manuals,
    load_jsonl,
    load_pdk_rules,
    load_project_docs,
)

# ---------------------------------------------------------------------------
# Fixtures – temp JSONL helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_pdk_jsonl(tmp_path):
    """Create a temporary PDK JSONL file."""
    path = tmp_path / "pdk_rules.jsonl"
    lines = [
        {"text": "M3 pitch for N5 is 36nm.", "metadata": {"category": "PDK", "node": "N5", "tool": "Innovus"}},
        {"text": "M3 pitch for N7 is 40nm.", "metadata": {"category": "PDK", "node": "N7", "tool": "Innovus"}},
    ]
    path.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def sample_eda_jsonl(tmp_path):
    """Create a temporary EDA JSONL file."""
    path = tmp_path / "eda_manuals.jsonl"
    lines = [
        {"text": "Innovus command floorPlan usage.", "metadata": {"category": "EDA", "tool": "Innovus"}},
    ]
    path.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def sample_project_jsonl(tmp_path):
    """Create a temporary project docs JSONL file."""
    path = tmp_path / "project_docs.jsonl"
    lines = [
        {"text": "Proj_A targets N5 with Innovus.", "metadata": {"category": "Project_Doc", "project_id": "Proj_A", "node": "N5", "tool": "Innovus"}},
    ]
    path.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests – IngestionDocument model
# ---------------------------------------------------------------------------

class TestIngestionDocument:
    def test_basic_construction(self):
        doc = IngestionDocument(text="hello", metadata={"category": "PDK"})
        assert doc.text == "hello"
        assert doc.metadata["category"] == "PDK"
        assert doc.source is None

    def test_with_source(self):
        doc = IngestionDocument(text="x", metadata={}, source="/some/file.jsonl")
        assert doc.source == "/some/file.jsonl"

    def test_default_metadata(self):
        doc = IngestionDocument(text="x")
        assert doc.metadata == {}


# ---------------------------------------------------------------------------
# Tests – load_jsonl
# ---------------------------------------------------------------------------

class TestLoadJsonl:
    def test_loads_valid_lines(self, sample_pdk_jsonl):
        docs = load_jsonl(sample_pdk_jsonl)
        assert len(docs) == 2
        assert all(isinstance(d, IngestionDocument) for d in docs)
        assert docs[0].text == "M3 pitch for N5 is 36nm."
        assert docs[0].metadata["node"] == "N5"

    def test_source_is_set(self, sample_pdk_jsonl):
        docs = load_jsonl(sample_pdk_jsonl)
        assert all(d.source == str(sample_pdk_jsonl) for d in docs)

    def test_skips_blank_lines(self, tmp_path):
        path = tmp_path / "blank.jsonl"
        path.write_text('\n\n{"text": "ok", "metadata": {"category": "X"}}\n\n', encoding="utf-8")
        docs = load_jsonl(path)
        assert len(docs) == 1

    def test_skips_malformed_json(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text('not-json\n{"text": "ok", "metadata": {}}\n', encoding="utf-8")
        docs = load_jsonl(path)
        assert len(docs) == 1
        assert docs[0].text == "ok"

    def test_skips_entry_without_text(self, tmp_path):
        path = tmp_path / "no_text.jsonl"
        path.write_text('{"metadata": {"category": "X"}}\n{"text": "good", "metadata": {}}\n', encoding="utf-8")
        docs = load_jsonl(path)
        assert len(docs) == 1
        assert docs[0].text == "good"

    def test_skips_entry_with_empty_text(self, tmp_path):
        path = tmp_path / "empty_text.jsonl"
        path.write_text('{"text": "", "metadata": {}}\n', encoding="utf-8")
        docs = load_jsonl(path)
        assert len(docs) == 0

    def test_skips_entry_with_non_dict_metadata(self, tmp_path):
        path = tmp_path / "bad_meta.jsonl"
        path.write_text('{"text": "x", "metadata": "oops"}\n', encoding="utf-8")
        docs = load_jsonl(path)
        assert len(docs) == 0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_jsonl("/nonexistent/path.jsonl")

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        docs = load_jsonl(path)
        assert docs == []


# ---------------------------------------------------------------------------
# Tests – typed loaders
# ---------------------------------------------------------------------------

class TestTypedLoaders:
    def test_load_pdk_rules(self, sample_pdk_jsonl):
        docs = load_pdk_rules(sample_pdk_jsonl)
        assert len(docs) == 2
        assert all(d.metadata.get("category") == "PDK" for d in docs)

    def test_load_eda_manuals(self, sample_eda_jsonl):
        docs = load_eda_manuals(sample_eda_jsonl)
        assert len(docs) == 1
        assert docs[0].metadata["category"] == "EDA"

    def test_load_project_docs(self, sample_project_jsonl):
        docs = load_project_docs(sample_project_jsonl)
        assert len(docs) == 1
        assert docs[0].metadata["category"] == "Project_Doc"
        assert docs[0].metadata["project_id"] == "Proj_A"


# ---------------------------------------------------------------------------
# Tests – load_all_documents
# ---------------------------------------------------------------------------

class TestLoadAllDocuments:
    def test_merges_all_sources(self, sample_pdk_jsonl, sample_eda_jsonl, sample_project_jsonl):
        docs = load_all_documents(sample_pdk_jsonl, sample_eda_jsonl, sample_project_jsonl)
        assert len(docs) == 4  # 2 PDK + 1 EDA + 1 Project

        categories = [d.metadata["category"] for d in docs]
        assert categories.count("PDK") == 2
        assert categories.count("EDA") == 1
        assert categories.count("Project_Doc") == 1


# ---------------------------------------------------------------------------
# Tests – integration against real dev_data files
# ---------------------------------------------------------------------------

class TestRealDevData:
    """Smoke tests against the actual seed data files if present."""

    @pytest.fixture(autouse=True)
    def _check_files(self):
        # Walk up to repo root so the path works regardless of cwd.
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._base = os.path.join(repo_root, "jbprag", "dev_data")
        if not os.path.isdir(self._base):
            pytest.skip("dev_data directory not found")

    def test_pdk_rules(self):
        path = os.path.join(self._base, "pdk_rules.jsonl")
        if not os.path.exists(path):
            pytest.skip("pdk_rules.jsonl not found")
        docs = load_pdk_rules(path)
        assert len(docs) > 0
        assert all(d.metadata.get("category") == "PDK" for d in docs)

    def test_eda_manuals(self):
        path = os.path.join(self._base, "eda_manuals.jsonl")
        if not os.path.exists(path):
            pytest.skip("eda_manuals.jsonl not found")
        docs = load_eda_manuals(path)
        assert len(docs) > 0
        assert all(d.metadata.get("category") == "EDA" for d in docs)

    def test_project_docs(self):
        path = os.path.join(self._base, "project_docs.jsonl")
        if not os.path.exists(path):
            pytest.skip("project_docs.jsonl not found")
        docs = load_project_docs(path)
        assert len(docs) > 0
        assert all(d.metadata.get("category") == "Project_Doc" for d in docs)

    def test_load_all(self):
        pdk = os.path.join(self._base, "pdk_rules.jsonl")
        eda = os.path.join(self._base, "eda_manuals.jsonl")
        proj = os.path.join(self._base, "project_docs.jsonl")
        if not all(os.path.exists(p) for p in [pdk, eda, proj]):
            pytest.skip("Not all dev_data files present")
        docs = load_all_documents(pdk, eda, proj)
        assert len(docs) == 7  # 3 PDK + 2 EDA + 2 Project
