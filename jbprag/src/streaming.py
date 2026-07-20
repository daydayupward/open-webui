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
    
    chunks_yielded = 0
    try:
        async for event in graph.astream_events(initial_state, version="v2"):
            event_type = event.get("event")
            metadata = event.get("metadata", {})
            name = event.get("name")
            
            if event_type == "on_chat_model_stream":
                name = metadata.get("langgraph_node") or event.get("name") or ""
                allowed_nodes = [
                    ExpertRoute.PDK,
                    ExpertRoute.EDA,
                    ExpertRoute.METRICS,
                    "generate",
                    "refine",
                    "summarize",
                    "clarify",
                    "finalizer",
                ]
                if name in allowed_nodes:
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
                            chunks_yielded += 1
            elif event_type == "on_chain_end" and name in ("LangGraph", "__root__"):
                data = event.get("data", {})
                output = data.get("output")
                if isinstance(output, dict):
                    retrieved_docs = output.get("retrieved_docs", [])
                    if retrieved_docs:
                        sources_list = []
                        collection_map = {
                            "EDA": "eda_manuals",
                            "Script": "eda_manuals",
                            "Literature": "eda_manuals",
                            "PDK": "pdk_rules",
                            "StdCell": "pdk_rules",
                            "SRAM": "pdk_rules",
                            "IP": "pdk_rules",
                            "PROJECT": "project_docs",
                            "Project_Doc": "project_docs",
                            "Platform_Flow": "project_docs",
                        }
                        
                        import os
                        import urllib.parse

                        for doc in retrieved_docs:
                            page_content = doc.get("page_content") or doc.get("content") or ""
                            meta = doc.get("metadata", {}) or {}
                            raw_source_name = meta.get("name") or meta.get("source") or "Document"
                            source_name = os.path.basename(raw_source_name) if ("/" in raw_source_name or "\\" in raw_source_name) else raw_source_name
                            
                            file_id = meta.get("file_id")
                            page = meta.get("page")
                            doc_id = meta.get("doc_id")
                            category = meta.get("category", "eda_manuals")
                            collection = collection_map.get(category, "eda_manuals")

                            # Build context_url so CitationDrawer can fetch highlighted context
                            context_url = None
                            if doc_id:
                                chunk_hint = urllib.parse.quote(page_content[:200], safe="")
                                context_url = (
                                    f"http://localhost:8000/v1/documents/context"
                                    f"?doc_id={doc_id}"
                                    f"&collection={collection}"
                                    f"&chunk_text={chunk_hint}"
                                )

                            sources_list.append({
                                "source": {
                                    "name": source_name,
                                    "id": file_id or source_name
                                },
                                "document": [page_content],
                                "metadata": [
                                    {
                                        "source": file_id or source_name,
                                        "name": source_name,
                                        "page": page,
                                        "file_id": file_id,
                                        "doc_id": doc_id,
                                        "collection": collection,
                                        "context_url": context_url,
                                    }
                                ]
                            })

                        if sources_list:
                            yield f"data: {json.dumps({'sources': sources_list})}\n\n"

                    if "final_answer" in output and "route" in output:
                        final_answer = output["final_answer"]
                        if not chunks_yielded and final_answer:
                            chunk_data = format_openai_chunk(
                                completion_id=completion_id,
                                content=final_answer,
                                created_time=created_time,
                                model_name=model_name,
                                finish_reason=None
                            )
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                            chunks_yielded += 1
                            
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
