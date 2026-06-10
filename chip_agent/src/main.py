from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from src.graph import build_graph
from langchain_core.messages import HumanMessage
import time
import uuid

app = FastAPI()
graph = build_graph()

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = "default"

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    last_msg = req.messages[-1]["content"]
    result = graph.invoke({"messages": [HumanMessage(content=last_msg)]})
    final_text = result["messages"][-1].content
    
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": final_text
            },
            "finish_reason": "stop"
        }]
    }
