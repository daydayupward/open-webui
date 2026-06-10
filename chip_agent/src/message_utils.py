from typing import List, Union, Dict, Any
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from src.api_models import ChatMessage

def openai_to_langchain(messages: List[Union[ChatMessage, Dict[str, Any]]]) -> List[AnyMessage]:
    lc_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
        else:
            role = msg.role
            content = msg.content
            
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role in ["assistant", "ai"]:
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    return lc_messages
