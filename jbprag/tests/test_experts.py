import pytest
from unittest.mock import patch, MagicMock
from src.experts.eda_script_expert import eda_script_expert_node
from src.experts.metrics_analyst import metrics_analyst_node
from langchain_core.messages import HumanMessage, AIMessage

@patch("src.experts.eda_script_subgraph.aretrieve_eda_manuals")
@patch("src.experts.eda_script_subgraph.get_llm")
@pytest.mark.anyio
async def test_eda_script_expert(mock_get_llm, mock_retrieve):
    from unittest.mock import AsyncMock
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="set_db_floplan_mode -mode user")
    mock_get_llm.return_value = mock_llm
    
    mock_retrieve.return_value = {
        "chunks": [],
        "logs": {"step": "mock"}
    }

    state = {
        "messages": [HumanMessage(content="Innovus floorplan command")],
        "metadata": {"tool": "Innovus"}
    }
    result = await eda_script_expert_node(state)
    assert len(result["messages"]) >= 1
    assert "set_db_floplan_mode" in result["messages"][0].content or "floorplan" in result["messages"][0].content

@patch("src.experts.metrics_subgraph.aretrieve_project_docs")
@patch("src.experts.metrics_subgraph.aexecute_read_query")
@patch("src.experts.metrics_subgraph.validate_sql_query")
@patch("src.experts.metrics_subgraph.get_llm")
@pytest.mark.anyio
async def test_metrics_analyst(mock_get_llm, mock_validate, mock_execute, mock_retrieve):
    from unittest.mock import AsyncMock
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        AIMessage(content="sql"),  # route classification
        AIMessage(content="SELECT wns, tns, power, area FROM project_metrics WHERE project_id = 'P100';"),  # SQL generation
        AIMessage(content="Design PPA: WNS is -0.15ns, TNS is -1.2ns, power is 1.2W."),  # summarize
    ]
    mock_get_llm.return_value = mock_llm
    mock_validate.return_value = True
    mock_execute.return_value = [{"wns": -0.15, "tns": -1.2, "power": 1.2, "area": 5000}]
    mock_retrieve.return_value = {
        "chunks": [],
        "logs": {"step": "Project Retrieval", "status": "success"},
    }

    state = {
        "messages": [HumanMessage(content="Timing report metrics")],
        "metadata": {"project_id": "P100"},
    }
    result = await metrics_analyst_node(state)
    assert len(result["messages"]) >= 1
    assert "final_answer" in result
    assert "retrieved_docs" in result
    assert "tool_logs" in result
