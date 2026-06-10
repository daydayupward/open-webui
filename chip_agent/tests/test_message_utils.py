from src.message_utils import openai_to_langchain
from src.api_models import ChatMessage
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

def test_openai_to_langchain_pydantic():
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

def test_openai_to_langchain_dicts():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "ai", "content": "Hi there!"},
        {"role": "unknown", "content": "Fallback message"},
    ]
    
    lc_messages = openai_to_langchain(messages)
    assert len(lc_messages) == 4
    
    assert isinstance(lc_messages[0], SystemMessage)
    assert isinstance(lc_messages[1], HumanMessage)
    assert isinstance(lc_messages[2], AIMessage)
    assert isinstance(lc_messages[3], HumanMessage)
    assert lc_messages[3].content == "Fallback message"
