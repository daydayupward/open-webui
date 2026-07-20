import pytest
import json
import os

@pytest.mark.anyio
async def test_pdk_rules_format():
    file_path = os.path.join(os.path.dirname(__file__), "../dev_data/pdk_rules.jsonl")
    assert os.path.exists(file_path)
    with open(file_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            assert "text" in data
            assert "metadata" in data
            assert data["metadata"]["category"] == "PDK"
            assert "node" in data["metadata"]

@pytest.mark.anyio
async def test_eda_manuals_format():
    file_path = os.path.join(os.path.dirname(__file__), "../dev_data/eda_manuals.jsonl")
    assert os.path.exists(file_path)
    with open(file_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            assert "text" in data
            assert "metadata" in data
            assert data["metadata"]["category"] == "EDA"
            assert "tool" in data["metadata"]

@pytest.mark.anyio
async def test_project_docs_format():
    file_path = os.path.join(os.path.dirname(__file__), "../dev_data/project_docs.jsonl")
    assert os.path.exists(file_path)
    with open(file_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            assert "text" in data
            assert "metadata" in data
            assert data["metadata"]["category"] == "Project_Doc"
            assert "project_id" in data["metadata"]
