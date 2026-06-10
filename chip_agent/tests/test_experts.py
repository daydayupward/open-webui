from unittest.mock import patch, MagicMock
from src.experts.eda_script_expert import eda_script_expert_node
from src.experts.metrics_analyst import metrics_analyst_node
from langchain_core.messages import HumanMessage, AIMessage

@patch("src.experts.eda_script_expert.get_llm")
def test_eda_script_expert(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="set_db_floplan_mode -mode user")
    mock_get_llm.return_value = mock_llm

    state = {"messages": [HumanMessage(content="Innovus floorplan command")]}
    result = eda_script_expert_node(state)
    assert len(result["messages"]) == 1
    assert "floorplan" in result["messages"][0].content or "set_db_floplan_mode" in result["messages"][0].content

@patch("src.experts.metrics_analyst.get_llm")
def test_metrics_analyst(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="Design PPA: power is 1.2W")
    mock_get_llm.return_value = mock_llm

    state = {"messages": [HumanMessage(content="Timing report metrics")]}
    result = metrics_analyst_node(state)
    assert len(result["messages"]) == 1
    assert "power" in result["messages"][0].content
