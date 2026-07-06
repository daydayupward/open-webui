from unittest.mock import patch, AsyncMock
import pytest
from src.message_utils import openai_to_langchain, preprocess_multimodal_messages
from src.api_models import ChatMessage
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

@pytest.mark.anyio
async def test_openai_to_langchain_pydantic():
    messages = [
        ChatMessage(role="system", content="You are helpful."),
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there!"),
        ChatMessage(role="user", content="How are you?"),
    ]
    
    lc_messages = openai_to_langchain(messages)
    assert len(lc_messages) == 4
    
    assert isinstance(lc_messages[0], SystemMessage)
    assert lc_messages[0].content == "You are helpful."
    
    assert isinstance(lc_messages[1], HumanMessage)
    assert lc_messages[1].content == "Hello"
    
    assert isinstance(lc_messages[2], AIMessage)
    assert lc_messages[2].content == "Hi there!"
    
    assert isinstance(lc_messages[3], HumanMessage)
    assert lc_messages[3].content == "How are you?"

@pytest.mark.anyio
async def test_openai_to_langchain_dicts():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "ai", "content": "Hi there!"},
        {"role": "unknown", "content": "Fallback message"},
        {"role": "user", "content": [{"type": "text", "text": "Multimodal question"}]},
        {"role": "assistant", "content": None}
    ]
    
    lc_messages = openai_to_langchain(messages)
    assert len(lc_messages) == 6
    
    assert isinstance(lc_messages[0], SystemMessage)
    assert isinstance(lc_messages[1], HumanMessage)
    assert isinstance(lc_messages[2], AIMessage)
    assert isinstance(lc_messages[3], HumanMessage)
    assert lc_messages[3].content == "Fallback message"
    assert isinstance(lc_messages[4], HumanMessage)
    assert isinstance(lc_messages[4].content, list)
    assert lc_messages[5].content == ""

@pytest.mark.anyio
@patch("src.message_utils.get_visual_llm")
async def test_preprocess_multimodal_messages(mock_get_visual_llm):
    # Mock visual LLM response
    mock_vllm = AsyncMock()
    mock_vllm.ainvoke.return_value = AIMessage(content="[VLM Description] Spacing violation on Metal 1 (M1) is 0.08um.")
    mock_get_visual_llm.return_value = mock_vllm
    
    # Input messages with image
    messages = [
        HumanMessage(content=[
            {"type": "text", "text": "What is this DRC error?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,imagedata"}}
        ])
    ]
    
    processed = await preprocess_multimodal_messages(messages)
    assert len(processed) == 1
    assert "What is this DRC error?" in processed[0].content
    assert "[版图截图描述与DRC错误提取]" in processed[0].content
    assert "M1" in processed[0].content
    
    mock_get_visual_llm.assert_called_once()
