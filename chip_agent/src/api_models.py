from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class RoleEnum(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"
    function = "function"

class ChatMessage(BaseModel):
    role: RoleEnum
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[dict]] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "default"
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.0

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = "stop"

class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Optional[Usage] = None
