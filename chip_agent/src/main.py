import time
import uuid
from fastapi import FastAPI

from src.graph import build_graph
from src.api_models import ChatRequest
from src.message_utils import openai_to_langchain
from src.response_formatter import format_openai_response

app = FastAPI()
graph = build_graph()

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "chip-agentic-rag",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "chip-agent"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    request_id = uuid.uuid4().hex
    lc_messages = openai_to_langchain(req.messages)
    
    initial_state = {
        "messages": lc_messages,
        "request_id": request_id,
        "route": "",
        "metadata": {},
        "retrieved_docs": [],
        "tool_logs": [],
        "final_answer": "",
        "errors": []
    }
    
    result = graph.invoke(initial_state)
    
    response = format_openai_response(result, req.model)
    return response.model_dump()
