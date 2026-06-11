import json
import uuid
import time
from typing import AsyncGenerator
from langchain_core.messages import AIMessageChunk
from src.response_formatter import format_openai_chunk
from src.constants import ExpertRoute

async def astream_chat_completion_events(graph, initial_state, model_name: str) -> AsyncGenerator[str, None]:
    created_time = int(time.time())
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    
    try:
        async for event in graph.astream_events(initial_state, version="v2"):
            event_type = event.get("event")
            name = event.get("name")
            
            if event_type == "on_chat_model_stream":
                metadata = event.get("metadata", {})
                name = event.get("name") or metadata.get("langgraph_node", "")
                if name in [ExpertRoute.PDK, ExpertRoute.EDA, "refinement_agent", ExpertRoute.METRICS, "summarizer", "text_to_sql", "finalizer"]:
                    data = event.get("data", {})
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        content = chunk.content
                        if content:
                            chunk_data = format_openai_chunk(
                                completion_id=completion_id,
                                content=content,
                                created_time=created_time,
                                model_name=model_name,
                                finish_reason=None
                            )
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            
    except Exception as e:
        error_data = format_openai_chunk(
            completion_id=completion_id,
            content=f"\n[Error during streaming: {e}]",
            created_time=created_time,
            model_name=model_name,
            finish_reason="error"
        )
        yield f"data: {json.dumps(error_data)}\n\n"
        
    final_chunk = format_openai_chunk(
        completion_id=completion_id,
        content=None,
        created_time=created_time,
        model_name=model_name,
        finish_reason="stop"
    )
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"
