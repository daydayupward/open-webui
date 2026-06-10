from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage
from src.metadata import QueryMetadata, normalize_metadata
from src.supervisor import parse_json_safely, run_supervisor

def test_metadata_normalization():
    # Test Node Normalization
    meta1 = QueryMetadata(category="pdk", node="n5", tool="innovus", project_id="proja")
    norm1 = normalize_metadata(meta1)
    assert norm1.category == "PDK"
    assert norm1.node == "N5"
    assert norm1.tool == "Innovus"
    assert norm1.project_id == "Proj_A"

    # Test Tool / Project Normalization variations
    meta2 = QueryMetadata(category="eda", node="7nm", tool="icc2", project_id="project_b")
    norm2 = normalize_metadata(meta2)
    assert norm2.category == "EDA"
    assert norm2.node == "N7"
    assert norm2.tool == "ICC2"
    assert norm2.project_id == "Proj_B"
    
    # Test Fallback and general category
    meta3 = QueryMetadata(category="general", node="n16", tool="other_tool", project_id="other_proj")
    norm3 = normalize_metadata(meta3)
    assert norm3.category == "General"
    assert norm3.node == "N16"
    assert norm3.tool == "Other_tool"
    assert norm3.project_id == "other_proj"

def test_parse_json_safely():
    # Standard JSON
    assert parse_json_safely('{"next": "pdk_expert"}') == {"next": "pdk_expert"}
    # Codeblock JSON
    assert parse_json_safely('```json\n{"next": "eda_expert"}\n```') == {"next": "eda_expert"}
    # Plain text wrapping JSON
    assert parse_json_safely('Sure, here is the routing:\n{"next": "metrics_analyst"}') == {"next": "metrics_analyst"}

@patch("src.supervisor.get_llm")
def test_run_supervisor_success(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content='''{
            "next": "pdk_expert",
            "metadata": {
                "category": "pdk",
                "node": "n5",
                "tool": null,
                "project_id": null,
                "confidence": 0.95,
                "missing_fields": []
            }
        }'''
    )
    mock_get_llm.return_value = mock_llm
    
    result = run_supervisor([HumanMessage(content="What is the metal pitch of N5 M3?")])
    assert result["route"] == "pdk_expert"
    assert result["metadata"]["category"] == "PDK"
    assert result["metadata"]["node"] == "N5"
    assert result["metadata"]["tool"] is None
    assert result["metadata"]["confidence"] == 0.95

@patch("src.supervisor.get_llm")
def test_run_supervisor_fallback_on_invalid_json(mock_get_llm):
    mock_llm = MagicMock()
    # Invalid JSON output
    mock_llm.invoke.return_value = AIMessage(content="Sorry, I cannot route this query correctly.")
    mock_get_llm.return_value = mock_llm
    
    result = run_supervisor([HumanMessage(content="Invalid input text.")])
    # Should fall back to default route and metadata
    assert result["route"] == "finalizer"
    assert result["metadata"]["category"] == "General"
    assert result["metadata"]["node"] is None
