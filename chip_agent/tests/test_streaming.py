import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import AIMessageChunk
from src.streaming import astream_chat_completion_events

@pytest.mark.asyncio
@pytest.mark.anyio
async def test_astream_chat_completion_events():
    mock_graph = MagicMock()
    
    events = [
        {
            "event": "on_chat_model_stream",
            "metadata": {"langgraph_node": "supervisor"},
            "data": {"chunk": AIMessageChunk(content='{"next": "pdk_expert"}')}
        },
        {
            "event": "on_chat_model_stream",
            "metadata": {"langgraph_node": "pdk_expert"},
            "data": {"chunk": AIMessageChunk(content="The metal")}
        },
        {
            "event": "on_chat_model_stream",
            "metadata": {"langgraph_node": "pdk_expert"},
            "data": {"chunk": AIMessageChunk(content=" pitch is 36nm.")}
        }
    ]
    
    async def mock_astream_events(*args, **kwargs):
        for event in events:
            yield event
            
    mock_graph.astream_events = mock_astream_events
    
    initial_state = {"messages": []}
    
    chunks = []
    async for chunk in astream_chat_completion_events(mock_graph, initial_state, "default"):
        chunks.append(chunk)
        
    assert len(chunks) == 4
    assert "The metal" in chunks[0]
    assert "pitch is 36nm." in chunks[1]
    assert "stop" in chunks[2]
    assert "[DONE]" in chunks[3]
