import time
import uuid
from src.api_models import ChatCompletionResponse, ChatCompletionResponseChoice, ChatMessage

def format_openai_response(state: dict, model_name: str) -> ChatCompletionResponse:
    final_answer = state.get("final_answer", "")
    if not final_answer:
        for msg in reversed(state.get("messages", [])):
            # Handle LangChain message objects
            msg_type = getattr(msg, "type", None)
            if msg_type == "ai" or msg.__class__.__name__ == "AIMessage":
                final_answer = msg.content
                break
                
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
    
    return ChatCompletionResponse(
        id=response_id,
        object="chat.completion",
        created=int(time.time()),
        model=model_name,
        choices=[choice]
    )
