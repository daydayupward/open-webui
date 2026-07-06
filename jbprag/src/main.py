import time
import uuid
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse

from contextlib import asynccontextmanager
from src.graph import build_graph
from src.api_models import ChatRequest
from src.message_utils import openai_to_langchain, preprocess_multimodal_messages
from src.response_formatter import format_openai_response
from src.streaming import astream_chat_completion_events
from src.admin_db import init_db
from src.admin_router import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(admin_router)
graph = build_graph()

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "jbprag",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "jbprag"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    try:
        request_id = uuid.uuid4().hex
        lc_messages = openai_to_langchain(req.messages)
        lc_messages = await preprocess_multimodal_messages(lc_messages)
        
        initial_state = {
            "messages": lc_messages,
            "request_id": request_id,
            "temperature": req.temperature,
            "route": "",
            "metadata": {},
            "retrieved_docs": [],
            "tool_logs": [],
            "final_answer": "",
            "errors": []
        }
        
        if req.stream:
            generator = astream_chat_completion_events(graph, initial_state, req.model)
            return StreamingResponse(generator, media_type="text/event-stream")
            
        result = await graph.ainvoke(initial_state)
        
        response = format_openai_response(result, req.model)
        return response.model_dump()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": str(e),
                    "type": "internal_error",
                    "code": 500
                }
            }
        )
