from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from src.metadata import QueryMetadata, normalize_metadata
from src.supervisor import parse_json_safely, arun_supervisor

@pytest.mark.anyio
async def test_metadata_normalization():
    # Test Node Normalization
    meta1 = QueryMetadata(categories=["pdk"], node="n5", tool="innovus", project_id="proja")
    norm1 = normalize_metadata(meta1)
    assert "PDK" in norm1.categories
    assert norm1.node == "N5"
    assert norm1.tool == "Innovus"
    assert norm1.project_id == "Proj_A"

    # Test Tool / Project Normalization variations
    meta2 = QueryMetadata(categories=["eda"], node="7nm", tool="icc2", project_id="project_b")
    norm2 = normalize_metadata(meta2)
    assert "EDA" in norm2.categories
    assert norm2.node == "N7"
    assert norm2.tool == "ICC2"
    assert norm2.project_id == "Proj_B"
    
    # Test Fallback and general categories
    meta3 = QueryMetadata(categories=["general"], node="n16", tool="other_tool", project_id="other_proj")
    norm3 = normalize_metadata(meta3)
    assert "Literature" in norm3.categories
    assert norm3.node == "N16"
    assert norm3.tool == "Other_tool"
    assert norm3.project_id == "other_proj"

@pytest.mark.anyio
async def test_parse_json_safely():
    # Standard JSON
    assert parse_json_safely('{"next": "pdk_expert"}') == {"next": "pdk_expert"}
    # Codeblock JSON
    assert parse_json_safely('```json\n{"next": "eda_expert"}\n```') == {"next": "eda_expert"}
    # Plain text wrapping JSON
    assert parse_json_safely('Sure, here is the routing:\n{"next": "metrics_analyst"}') == {"next": "metrics_analyst"}

@patch("src.supervisor.get_llm")
@pytest.mark.anyio
async def test_run_supervisor_success(mock_get_llm):
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content='''{
            "next": "pdk_expert",
            "metadata": {
                "categories": ["pdk"],
                "node": "n5",
                "tool": null,
                "project_id": null,
                "confidence": 0.95,
                "missing_fields": []
            }
        }'''
    )
    mock_get_llm.return_value = mock_llm
    
    result = await arun_supervisor([HumanMessage(content="What is the metal pitch of N5 M3?")])
    assert result["route"] == "pdk_expert"
    assert "PDK" in result["metadata"]["categories"]
    assert result["metadata"]["node"] == "N5"
    assert result["metadata"]["tool"] is None
    assert result["metadata"]["confidence"] == 0.95

@patch("src.supervisor.get_llm")
@pytest.mark.anyio
async def test_run_supervisor_fallback_on_invalid_json(mock_get_llm):
    mock_llm = AsyncMock()
    # Invalid JSON output
    mock_llm.ainvoke.return_value = AIMessage(content="Sorry, I cannot route this query correctly.")
    mock_get_llm.return_value = mock_llm
    
    result = await arun_supervisor([HumanMessage(content="Invalid input text.")])
    # Should fall back to default route and metadata
    assert result["route"] == "finalizer"
    assert "Literature" in result["metadata"]["categories"]
    assert result["metadata"]["node"] is None
