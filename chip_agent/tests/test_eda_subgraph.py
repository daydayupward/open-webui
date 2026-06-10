import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from src.tools.eda_lint import lint_eda_script
from src.retrieval.eda_retriever import retrieve_eda_manuals
from src.experts.eda_script_subgraph import build_eda_subgraph, extract_script

def test_extract_script():
    # Test extraction with markdown formatting
    content_with_md = "Here is the script:\n```tcl\nfloorPlan -r 1\n```\nHope this helps."
    assert extract_script(content_with_md) == "floorPlan -r 1"
    
    content_plain = "floorPlan -r 1"
    assert extract_script(content_plain) == "floorPlan -r 1"

def test_eda_linter():
    # Test bracket matching stack checks
    valid_script = "floorPlan -site core -r {1 0.7 10 10 10 10}"
    res = lint_eda_script(valid_script)
    assert res["passed"] is True
    assert len(res["issues"]) == 0
    
    invalid_script = "floorPlan -site core -r {1 0.7 10 10 10 10"
    res = lint_eda_script(invalid_script)
    assert res["passed"] is False
    assert any("Unclosed opening bracket" in issue for issue in res["issues"])
    
    # Test restricted commands
    restricted_script = "floorPlan -site core\nexec rm -rf /"
    res = lint_eda_script(restricted_script)
    assert res["passed"] is False
    assert any("Restricted command usage detected: 'exec'" in issue for issue in res["issues"])
    assert any("Restricted command usage detected: 'rm'" in issue for issue in res["issues"])

@patch("src.retrieval.eda_retriever.query_vector_store")
@patch("src.retrieval.eda_retriever.QwenRerankerClient")
def test_retrieve_eda_manuals(mock_reranker_class, mock_query_store):
    mock_doc = MagicMock()
    mock_doc.page_content = "Innovus floorPlan command syntax"
    mock_doc.metadata = {"category": "EDA", "tool": "Innovus"}
    mock_query_store.return_value = [mock_doc]
    
    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = lambda q, chunks, top_k: chunks
    mock_reranker_class.return_value = mock_reranker
    
    res = retrieve_eda_manuals("floorplan", {"tool": "Innovus"})
    assert res["logs"]["status"] == "success"
    assert len(res["chunks"]) == 1
    assert res["chunks"][0].page_content == "Innovus floorPlan command syntax"
    
    called_filter = mock_query_store.call_args[1]["filter"]
    assert called_filter["category"] == "EDA"
    assert called_filter["tool"] == "Innovus"

@patch("src.experts.eda_script_subgraph.retrieve_eda_manuals")
@patch("src.experts.eda_script_subgraph.get_llm")
def test_subgraph_success_first_attempt(mock_get_llm, mock_retrieve):
    # Mock retrieval
    mock_doc = MagicMock()
    mock_doc.page_content = "floorPlan info"
    mock_doc.metadata = {"category": "EDA", "tool": "Innovus"}
    
    mock_retrieve.return_value = {
        "chunks": [mock_doc],
        "logs": {"step": "EDA Retrieval"}
    }
    
    # Mock LLM to return valid script on first try
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="```tcl\nfloorPlan -r 1\n```")
    mock_get_llm.return_value = mock_llm
    
    subgraph = build_eda_subgraph()
    
    initial_state = {
        "messages": [HumanMessage(content="Generate floorplan script")],
        "query": "Generate floorplan script",
        "metadata": {"tool": "Innovus"},
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "linter_result": {},
        "previous_response": "",
        "final_answer": ""
    }
    
    result = subgraph.invoke(initial_state)
    
    assert result["iterations"] == 1
    assert result["linter_result"]["passed"] is True
    assert "floorPlan -r 1" in result["final_answer"]
    assert len(result["tool_logs"]) == 2  # 1 retrieval + 1 linter check
    assert result["tool_logs"][0]["step"] == "EDA Retrieval"
    assert result["tool_logs"][1]["step"] == "Linter Check (Iteration 1)"
    assert result["tool_logs"][1]["passed"] is True

@patch("src.experts.eda_script_subgraph.retrieve_eda_manuals")
@patch("src.experts.eda_script_subgraph.get_llm")
def test_subgraph_refinement_loop(mock_get_llm, mock_retrieve):
    mock_retrieve.return_value = {
        "chunks": [],
        "logs": {"step": "EDA Retrieval"}
    }
    
    # Mock LLM: return invalid script first, then valid script on second call (refine)
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        AIMessage(content="```tcl\nfloorPlan -r {1\n```"),  # Mismatched bracket
        AIMessage(content="```tcl\nfloorPlan -r {1}\n```")  # Fixed bracket
    ]
    mock_get_llm.return_value = mock_llm
    
    subgraph = build_eda_subgraph()
    
    initial_state = {
        "messages": [HumanMessage(content="Generate floorplan script")],
        "query": "Generate floorplan script",
        "metadata": {"tool": "Innovus"},
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "linter_result": {},
        "previous_response": "",
        "final_answer": ""
    }
    
    result = subgraph.invoke(initial_state)
    
    assert result["iterations"] == 2
    assert result["linter_result"]["passed"] is True
    assert "floorPlan -r {1}" in result["final_answer"]
    # 1 retrieval + 1 check (fail) + 1 check (pass) = 3 logs
    assert len(result["tool_logs"]) == 3
    assert result["tool_logs"][1]["passed"] is False
    assert result["tool_logs"][2]["passed"] is True

@patch("src.experts.eda_script_subgraph.retrieve_eda_manuals")
@patch("src.experts.eda_script_subgraph.get_llm")
def test_subgraph_max_iterations_threshold(mock_get_llm, mock_retrieve):
    mock_retrieve.return_value = {
        "chunks": [],
        "logs": {"step": "EDA Retrieval"}
    }
    
    # Mock LLM to always return invalid script (contains restricted command)
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="```tcl\nexec rm -rf /\n```")
    mock_get_llm.return_value = mock_llm
    
    subgraph = build_eda_subgraph()
    
    initial_state = {
        "messages": [HumanMessage(content="Generate floorplan script")],
        "query": "Generate floorplan script",
        "metadata": {"tool": "Innovus"},
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "linter_result": {},
        "previous_response": "",
        "final_answer": ""
    }
    
    result = subgraph.invoke(initial_state)
    
    # It should run 2 cycles of check and stop at iterations = 2
    assert result["iterations"] == 2
    assert result["linter_result"]["passed"] is False
    assert "exec rm -rf" in result["final_answer"]
    # 1 retrieval + 1 check (fail) + 1 check (fail) = 3 logs
    assert len(result["tool_logs"]) == 3
    assert result["tool_logs"][1]["passed"] is False
    assert result["tool_logs"][2]["passed"] is False
