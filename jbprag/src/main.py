import time
import uuid
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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

# Allow the Open WebUI frontend (and any localhost) to call our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/v1/documents/context")
async def get_document_context(
    doc_id: str = Query(..., description="doc_id of the document to fetch"),
    chunk_text: str = Query(None, description="Chunk text prefix to highlight (first 200 chars)"),
    collection: str = Query("eda_manuals", description="Vector collection name"),
):
    """
    Return all chunks of a document concatenated, with the queried chunk wrapped
    in <mark> tags so CitationDrawer can display highlighted context.
    """
    import html
    from src.sql.sql_client import execute_read_query

    try:
        rows = execute_read_query(
            """
            SELECT e.document, e.cmetadata
            FROM langchain_pg_collection c
            JOIN langchain_pg_embedding e ON e.collection_id = c.uuid
            WHERE c.name = %s
              AND e.cmetadata->>'doc_id' = %s
            ORDER BY e.cmetadata->>'chunk_id'
            """,
            (collection, doc_id),
            timeout=10.0
        )
    except Exception as ex:
        return JSONResponse(status_code=500, content={"error": str(ex)})

    if not rows:
        return JSONResponse(status_code=404, content={"error": "Document not found", "doc_id": doc_id})

    # Concatenate all chunks with paragraph breaks
    full_text = "\n\n".join(row["document"] or "" for row in rows)

    # If a chunk_text hint is provided, wrap that chunk in <mark> tags
    if chunk_text:
        needle = chunk_text[:200].strip()
        idx = full_text.find(needle)
        if idx >= 0:
            end_idx = idx + len(needle)
            chunk_end = full_text.find("\n\n", end_idx)
            if chunk_end < 0:
                chunk_end = len(full_text)
            matched = full_text[idx:chunk_end]
            safe_matched = html.escape(matched)
            before = html.escape(full_text[:idx])
            after = html.escape(full_text[chunk_end:])
            content = (
                f'<pre style="white-space:pre-wrap;font-family:inherit">'
                f'{before}'
                f'<mark id="citation-chunk-0" class="bg-yellow-200 dark:bg-yellow-900 text-inherit rounded-sm">'
                f'{safe_matched}'
                f'</mark>'
                f'{after}'
                f'</pre>'
            )
        else:
            content = f'<pre style="white-space:pre-wrap;font-family:inherit">{html.escape(full_text)}</pre>'
    else:
        content = f'<pre style="white-space:pre-wrap;font-family:inherit">{html.escape(full_text)}</pre>'

    return {"content": content, "chunk_count": len(rows)}
