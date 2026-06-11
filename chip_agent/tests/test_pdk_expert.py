import pytest
from unittest.mock import patch, MagicMock
from src.experts.pdk_expert import pdk_expert_node
from langchain_core.messages import HumanMessage, AIMessage
from src.retrieval.types import RetrievalChunk

@patch("src.experts.pdk_expert.get_llm")
@patch("src.experts.pdk_expert.aretrieve_pdk_rules")
@pytest.mark.anyio
async def test_pdk_expert_node(mock_retrieve, mock_get_llm):
    # Mock LLM
    from unittest.mock import AsyncMock
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="[PDK Expert] The M3 pitch for N5 is 36nm.")
    mock_get_llm.return_value = mock_llm
    
    # Mock Retriever
    mock_chunk = RetrievalChunk(
        page_content="N5 M3 metal pitch is 36nm.",
        metadata={"category": "PDK", "node": "N5"}
    )
    mock_retrieve.return_value = {
        "chunks": [mock_chunk],
        "logs": {"step": "PDK Retrieval", "status": "success"}
    }

    state = {
        "messages": [HumanMessage(content="What is N5 M3 pitch?")],
        "metadata": {"node": "N5", "category": "PDK"},
        "retrieved_docs": [],
        "tool_logs": []
    }
    result = await pdk_expert_node(state)
    
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert "[PDK Expert]" in result["messages"][0].content
    
    assert len(result["retrieved_docs"]) == 1
    assert result["retrieved_docs"][0]["page_content"] == "N5 M3 metal pitch is 36nm."
    assert len(result["tool_logs"]) == 1
    assert result["tool_logs"][0]["step"] == "PDK Retrieval"
    
    mock_retrieve.assert_called_once_with("What is N5 M3 pitch?", {"node": "N5", "category": "PDK"})
