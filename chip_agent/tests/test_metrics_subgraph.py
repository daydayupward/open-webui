"""Tests for the metrics subgraph."""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from src.experts.metrics_subgraph import (
    build_metrics_subgraph,
    route_node,
    generate_sql_node,
    validate_sql_node,
    execute_sql_node,
    retrieve_docs_node,
    summarize_node,
    clarify_node,
    route_after_classify,
    route_after_validate,
    route_after_sql,
    DB_SCHEMA,
)


# --- Unit tests for individual nodes ---


def test_route_node_missing_project_id():
    """Route node should return 'clarify' when project_id is missing."""
    state = {
        "query": "What is the WNS for my project?",
        "project_id": "",
        "metadata": {},
    }
    result = route_node(state)
    assert result["query_type"] == "clarify"
    assert result["tool_logs"][0]["routed_to"] == "clarify"


@patch("src.experts.metrics_subgraph.get_llm")
def test_route_node_sql_query(mock_get_llm):
    """Route node should classify metric queries as 'sql'."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="sql")
    mock_get_llm.return_value = mock_llm

    state = {
        "query": "What is the WNS for project P100?",
        "project_id": "P100",
        "metadata": {},
    }
    result = route_node(state)
    assert result["query_type"] == "sql"
    assert result["tool_logs"][0]["routed_to"] == "sql"


@patch("src.experts.metrics_subgraph.get_llm")
def test_route_node_docs_query(mock_get_llm):
    """Route node should classify documentation queries as 'docs'."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="docs")
    mock_get_llm.return_value = mock_llm

    state = {
        "query": "What methodology was used for timing closure?",
        "project_id": "P100",
        "metadata": {},
    }
    result = route_node(state)
    assert result["query_type"] == "docs"


@patch("src.experts.metrics_subgraph.get_llm")
def test_route_node_both_query(mock_get_llm):
    """Route node should classify mixed queries as 'both'."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="both")
    mock_get_llm.return_value = mock_llm

    state = {
        "query": "Show WNS trend and explain the methodology",
        "project_id": "P100",
        "metadata": {},
    }
    result = route_node(state)
    assert result["query_type"] == "both"


@patch("src.experts.metrics_subgraph.get_llm")
def test_route_node_unrecognized_defaults_to_both(mock_get_llm):
    """Route node should default to 'both' for unrecognized classifications."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="something_weird")
    mock_get_llm.return_value = mock_llm

    state = {
        "query": "ambiguous query",
        "project_id": "P100",
        "metadata": {},
    }
    result = route_node(state)
    assert result["query_type"] == "both"


@patch("src.experts.metrics_subgraph.get_llm")
def test_generate_sql_node(mock_get_llm):
    """Generate SQL node should produce SQL from natural language."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="SELECT wns, tns FROM project_metrics WHERE project_id = 'P100';"
    )
    mock_get_llm.return_value = mock_llm

    state = {
        "query": "Show WNS and TNS for project P100",
        "iterations": 0,
    }
    result = generate_sql_node(state)

    assert "SELECT" in result["generated_sql"]
    assert result["iterations"] == 1
    assert result["tool_logs"][0]["step"] == "Generate SQL (Iteration 1)"


@patch("src.experts.metrics_subgraph.get_llm")
def test_generate_sql_node_strips_markdown(mock_get_llm):
    """Generate SQL node should strip markdown code fences."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="```sql\nSELECT wns FROM project_metrics;\n```"
    )
    mock_get_llm.return_value = mock_llm

    state = {"query": "Get WNS", "iterations": 0}
    result = generate_sql_node(state)

    assert "```" not in result["generated_sql"]
    assert result["generated_sql"] == "SELECT wns FROM project_metrics;"


def test_validate_sql_node_valid():
    """Validate SQL node should accept valid SELECT queries."""
    state = {
        "generated_sql": "SELECT wns, tns FROM project_metrics WHERE project_id = 'P100';"
    }
    result = validate_sql_node(state)
    assert result["sql_valid"] is True
    assert result["sql_error"] == ""


def test_validate_sql_node_invalid_insert():
    """Validate SQL node should reject INSERT statements."""
    state = {"generated_sql": "INSERT INTO project_metrics (wns) VALUES (1.0);"}
    result = validate_sql_node(state)
    assert result["sql_valid"] is False
    assert "validation failed" in result["sql_error"].lower()


def test_validate_sql_node_invalid_table():
    """Validate SQL node should reject queries against non-allowlisted tables."""
    state = {"generated_sql": "SELECT * FROM users;"}
    result = validate_sql_node(state)
    assert result["sql_valid"] is False


@patch("src.experts.metrics_subgraph.execute_read_query")
def test_execute_sql_node_success(mock_execute):
    """Execute SQL node should return results on success."""
    mock_execute.return_value = [
        {"wns": -0.15, "tns": -1.2},
        {"wns": -0.10, "tns": -0.8},
    ]

    state = {
        "generated_sql": "SELECT wns, tns FROM project_metrics WHERE project_id = 'P100';",
        "project_id": "P100",
    }
    result = execute_sql_node(state)

    assert len(result["sql_results"]) == 2
    assert result["sql_results"][0]["wns"] == -0.15
    assert result["tool_logs"][0]["status"] == "success"
    assert result["tool_logs"][0]["row_count"] == 2


@patch("src.experts.metrics_subgraph.execute_read_query")
def test_execute_sql_node_error(mock_execute):
    """Execute SQL node should handle database errors gracefully."""
    mock_execute.side_effect = Exception("Connection refused")

    state = {
        "generated_sql": "SELECT wns FROM project_metrics;",
        "project_id": "P100",
    }
    result = execute_sql_node(state)

    assert result["sql_results"] == []
    assert result["tool_logs"][0]["status"] == "error"
    assert "Connection refused" in result["tool_logs"][0]["error"]


@patch("src.experts.metrics_subgraph.execute_read_query")
def test_execute_sql_node_injects_project_id(mock_execute):
    """Execute SQL node should inject project_id filter when missing."""
    mock_execute.return_value = [{"wns": -0.15}]

    state = {
        "generated_sql": "SELECT wns FROM project_metrics;",
        "project_id": "P100",
    }
    result = execute_sql_node(state)

    executed_sql = result["tool_logs"][0]["executed_sql"]
    assert "P100" in executed_sql
    assert "project_id" in executed_sql


@patch("src.experts.metrics_subgraph.retrieve_project_docs")
def test_retrieve_docs_node(mock_retrieve):
    """Retrieve docs node should return document chunks."""
    mock_chunk = MagicMock()
    mock_chunk.page_content = "Timing closure methodology"
    mock_chunk.metadata = {"category": "PROJECT", "project_id": "P100"}

    mock_retrieve.return_value = {
        "chunks": [mock_chunk],
        "logs": {"step": "Project Retrieval", "status": "success"},
    }

    state = {"query": "timing closure methodology", "project_id": "P100"}
    result = retrieve_docs_node(state)

    assert len(result["retrieved_docs"]) == 1
    assert result["retrieved_docs"][0]["content"] == "Timing closure methodology"
    mock_retrieve.assert_called_once_with("timing closure methodology", "P100")


@patch("src.experts.metrics_subgraph.get_llm")
def test_summarize_node_with_sql_results(mock_get_llm):
    """Summarize node should produce a summary from SQL results."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="The WNS for project P100 is -0.15ns and TNS is -1.2ns."
    )
    mock_get_llm.return_value = mock_llm

    state = {
        "query": "What is the WNS for project P100?",
        "sql_results": [{"wns": -0.15, "tns": -1.2}],
        "retrieved_docs": [],
    }
    result = summarize_node(state)

    assert "final_answer" in result
    assert "-0.15" in result["final_answer"]
    assert result["tool_logs"][0]["has_sql_results"] is True
    assert result["tool_logs"][0]["has_doc_results"] is False


@patch("src.experts.metrics_subgraph.get_llm")
def test_summarize_node_with_doc_results(mock_get_llm):
    """Summarize node should produce a summary from document retrieval."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content="The timing closure methodology used standard multi-corner optimization."
    )
    mock_get_llm.return_value = mock_llm

    state = {
        "query": "What methodology was used?",
        "sql_results": [],
        "retrieved_docs": [
            {"content": "Used multi-corner STA", "metadata": {}},
        ],
    }
    result = summarize_node(state)

    assert "methodology" in result["final_answer"].lower()
    assert result["tool_logs"][0]["has_sql_results"] is False
    assert result["tool_logs"][0]["has_doc_results"] is True


@patch("src.experts.metrics_subgraph.get_llm")
def test_summarize_node_no_data(mock_get_llm):
    """Summarize node should handle empty results."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="No data found.")
    mock_get_llm.return_value = mock_llm

    state = {
        "query": "Some query",
        "sql_results": [],
        "retrieved_docs": [],
    }
    result = summarize_node(state)

    assert result["final_answer"] == "No data found."


def test_clarify_node():
    """Clarify node should return a message asking for project_id."""
    state = {}
    result = clarify_node(state)

    assert "project id" in result["final_answer"].lower()
    assert result["tool_logs"][0]["reason"] == "Missing project_id"


# --- Conditional routing function tests ---


def test_route_after_classify_sql():
    assert route_after_classify({"query_type": "sql"}) == "generate_sql"


def test_route_after_classify_docs():
    assert route_after_classify({"query_type": "docs"}) == "retrieve_docs"


def test_route_after_classify_both():
    assert route_after_classify({"query_type": "both"}) == "generate_sql"


def test_route_after_classify_clarify():
    assert route_after_classify({"query_type": "clarify"}) == "clarify"


def test_route_after_validate_valid():
    assert route_after_validate({"sql_valid": True, "iterations": 1}) == "execute_sql"


def test_route_after_validate_invalid_retry():
    assert route_after_validate({"sql_valid": False, "iterations": 1}) == "generate_sql"


def test_route_after_validate_invalid_exhausted():
    assert route_after_validate({"sql_valid": False, "iterations": 2}) == "retrieve_docs"


def test_route_after_sql_both():
    assert route_after_sql({"query_type": "both"}) == "retrieve_docs"


def test_route_after_sql_sql_only():
    assert route_after_sql({"query_type": "sql"}) == "summarize"


# --- Integration tests with the compiled subgraph ---


@patch("src.experts.metrics_subgraph.retrieve_project_docs")
@patch("src.experts.metrics_subgraph.execute_read_query")
@patch("src.experts.metrics_subgraph.validate_sql_query")
@patch("src.experts.metrics_subgraph.get_llm")
def test_full_sql_flow(
    mock_get_llm, mock_validate, mock_execute, mock_retrieve
):
    """Test full SQL-only flow: route -> generate_sql -> validate -> execute -> summarize."""
    # Setup mocks
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="sql"),  # route classification
        AIMessage(content="SELECT wns, tns FROM project_metrics WHERE project_id = 'P100';"),  # SQL generation
        AIMessage(content="WNS is -0.15ns, TNS is -1.2ns."),  # summarize
    ]
    mock_get_llm.return_value = mock_llm
    mock_validate.return_value = True
    mock_execute.return_value = [{"wns": -0.15, "tns": -1.2}]

    subgraph = build_metrics_subgraph()

    initial_state = {
        "messages": [HumanMessage(content="What is WNS and TNS?")],
        "query": "What is WNS and TNS?",
        "metadata": {},
        "project_id": "P100",
        "query_type": "",
        "generated_sql": "",
        "sql_valid": False,
        "sql_error": "",
        "sql_results": [],
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "final_answer": "",
    }

    result = subgraph.invoke(initial_state)

    assert result["query_type"] == "sql"
    assert result["sql_valid"] is True
    assert len(result["sql_results"]) == 1
    assert "WNS" in result["final_answer"]
    mock_execute.assert_called_once()


@patch("src.experts.metrics_subgraph.retrieve_project_docs")
@patch("src.experts.metrics_subgraph.get_llm")
def test_full_docs_flow(mock_get_llm, mock_retrieve):
    """Test full docs-only flow: route -> retrieve_docs -> summarize."""
    mock_chunk = MagicMock()
    mock_chunk.page_content = "Multi-corner timing optimization methodology"
    mock_chunk.metadata = {"category": "PROJECT", "project_id": "P100"}

    mock_retrieve.return_value = {
        "chunks": [mock_chunk],
        "logs": {"step": "Project Retrieval", "status": "success"},
    }

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="docs"),  # route classification
        AIMessage(content="The methodology uses multi-corner timing optimization."),  # summarize
    ]
    mock_get_llm.return_value = mock_llm

    subgraph = build_metrics_subgraph()

    initial_state = {
        "messages": [HumanMessage(content="What methodology was used?")],
        "query": "What methodology was used?",
        "metadata": {},
        "project_id": "P100",
        "query_type": "",
        "generated_sql": "",
        "sql_valid": False,
        "sql_error": "",
        "sql_results": [],
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "final_answer": "",
    }

    result = subgraph.invoke(initial_state)

    assert result["query_type"] == "docs"
    assert len(result["retrieved_docs"]) == 1
    assert "methodology" in result["final_answer"].lower()
    mock_retrieve.assert_called_once()


@patch("src.experts.metrics_subgraph.retrieve_project_docs")
@patch("src.experts.metrics_subgraph.execute_read_query")
@patch("src.experts.metrics_subgraph.validate_sql_query")
@patch("src.experts.metrics_subgraph.get_llm")
def test_full_both_flow(
    mock_get_llm, mock_validate, mock_execute, mock_retrieve
):
    """Test full 'both' flow: route -> generate_sql -> validate -> execute -> retrieve_docs -> summarize."""
    mock_chunk = MagicMock()
    mock_chunk.page_content = "Timing closure approach"
    mock_chunk.metadata = {"category": "PROJECT", "project_id": "P100"}

    mock_retrieve.return_value = {
        "chunks": [mock_chunk],
        "logs": {"step": "Project Retrieval", "status": "success"},
    }

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="both"),  # route classification
        AIMessage(content="SELECT wns FROM project_metrics WHERE project_id = 'P100';"),  # SQL generation
        AIMessage(content="WNS is -0.15ns and the timing closure used multi-corner approach."),  # summarize
    ]
    mock_get_llm.return_value = mock_llm
    mock_validate.return_value = True
    mock_execute.return_value = [{"wns": -0.15}]

    subgraph = build_metrics_subgraph()

    initial_state = {
        "messages": [HumanMessage(content="WNS and methodology")],
        "query": "WNS and methodology",
        "metadata": {},
        "project_id": "P100",
        "query_type": "",
        "generated_sql": "",
        "sql_valid": False,
        "sql_error": "",
        "sql_results": [],
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "final_answer": "",
    }

    result = subgraph.invoke(initial_state)

    assert result["query_type"] == "both"
    assert result["sql_valid"] is True
    assert len(result["sql_results"]) == 1
    assert len(result["retrieved_docs"]) == 1
    assert "WNS" in result["final_answer"]
    mock_retrieve.assert_called_once()


@patch("src.experts.metrics_subgraph.get_llm")
def test_missing_project_id_flow(mock_get_llm):
    """Test that missing project_id routes to clarify."""
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    subgraph = build_metrics_subgraph()

    initial_state = {
        "messages": [HumanMessage(content="What is WNS?")],
        "query": "What is WNS?",
        "metadata": {},
        "project_id": "",
        "query_type": "",
        "generated_sql": "",
        "sql_valid": False,
        "sql_error": "",
        "sql_results": [],
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "final_answer": "",
    }

    result = subgraph.invoke(initial_state)

    assert result["query_type"] == "clarify"
    assert "project id" in result["final_answer"].lower()
    # LLM should not have been called (route_node short-circuits)
    mock_llm.invoke.assert_not_called()


@patch("src.experts.metrics_subgraph.execute_read_query")
@patch("src.experts.metrics_subgraph.validate_sql_query")
@patch("src.experts.metrics_subgraph.get_llm")
def test_sql_validation_retry_then_fallback(mock_get_llm, mock_validate, mock_execute):
    """Test that SQL validation failures trigger retries, then fallback to docs."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="sql"),  # route classification
        AIMessage(content="BAD SQL 1"),  # first SQL generation
        AIMessage(content="BAD SQL 2"),  # second SQL generation (retry)
        AIMessage(content="No SQL data available, sorry."),  # summarize after fallback
    ]
    mock_get_llm.return_value = mock_llm
    mock_validate.return_value = False  # Always fail validation

    # Mock retrieve_project_docs since fallback goes to docs
    with patch("src.experts.metrics_subgraph.retrieve_project_docs") as mock_retrieve:
        mock_retrieve.return_value = {
            "chunks": [],
            "logs": {"step": "Project Retrieval", "status": "success"},
        }

        subgraph = build_metrics_subgraph()

        initial_state = {
            "messages": [HumanMessage(content="Some query")],
            "query": "Some query",
            "metadata": {},
            "project_id": "P100",
            "query_type": "",
            "generated_sql": "",
            "sql_valid": False,
            "sql_error": "",
            "sql_results": [],
            "retrieved_docs": [],
            "tool_logs": [],
            "iterations": 0,
            "final_answer": "",
        }

        result = subgraph.invoke(initial_state)

    # Should have retried SQL twice (iterations=2), then fallen back to docs
    assert result["iterations"] == 2
    assert result["sql_valid"] is False
    assert result["final_answer"] != ""
