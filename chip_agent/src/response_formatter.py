import time
import uuid
from src.api_models import ChatCompletionResponse, ChatCompletionResponseChoice, ChatMessage, Usage

from src.message_utils import get_last_ai_content

def format_openai_response(state: dict, model_name: str) -> ChatCompletionResponse:
    final_answer = state.get("final_answer", "")
    if not final_answer:
        final_answer = get_last_ai_content(state.get("messages", []))
                
    response_id = state.get("request_id", "")
    if not response_id:
        response_id = f"chatcmpl-{uuid.uuid4().hex}"
    elif not response_id.startswith("chatcmpl-"):
        response_id = f"chatcmpl-{response_id}"
        
    choice = ChatCompletionResponseChoice(
        index=0,
        message=ChatMessage(role="assistant", content=final_answer),
        finish_reason="stop"
    )
    
    prompt_tokens = 0
    completion_tokens = 0
    for msg in state.get("messages", []):
        if hasattr(msg, "response_metadata") and "token_usage" in msg.response_metadata:
            token_usage = msg.response_metadata["token_usage"]
            prompt_tokens += token_usage.get("prompt_tokens", 0)
            completion_tokens += token_usage.get("completion_tokens", 0)
            
    total_tokens = prompt_tokens + completion_tokens

    return ChatCompletionResponse(
        id=response_id,
        object="chat.completion",
        created=int(time.time()),
        model=model_name,
        choices=[choice],
        usage=Usage(
            prompt_tokens=prompt_tokens, 
            completion_tokens=completion_tokens, 
            total_tokens=total_tokens
        )
    )

def format_openai_chunk(
    completion_id: str,
    content: str,
    created_time: int,
    model_name: str,
    finish_reason: str = None
) -> dict:
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created_time,
        "model": model_name,
        "choices": [{
            "index": 0,
            "delta": {"content": content} if content is not None else {},
            "finish_reason": finish_reason
        }]
    }
