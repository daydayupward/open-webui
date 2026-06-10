import os
from typing import List, Dict, Any, Optional
from src.settings import settings
from src.utils import get_embeddings
from src.vector_store import query_vector_store
from src.retrieval.types import RetrievalChunk
from src.retrieval.reranker import QwenRerankerClient


def retrieve_project_docs(
    query: str,
    project_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    fetch_k: int = 10,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Retrieves project-specific documentation using hard metadata filtering on
    category and project_id, followed by vector similarity search and reranking.

    Args:
        query: The search query text
        project_id: Required project identifier for filtering
        metadata: Optional additional metadata for filtering
        fetch_k: Number of initial results to fetch from vector store
        top_k: Number of results to return after reranking

    Returns:
        Dict with 'chunks' (List[RetrievalChunk]) and 'logs' (Dict)
    """
    if not project_id:
        raise ValueError("project_id is required for project document retrieval")

    db_filter = {
        "category": "PROJECT",
        "project_id": project_id
    }

    # Apply additional metadata filters if provided
    if metadata:
        for key, value in metadata.items():
            if key not in db_filter and value is not None:
                db_filter[key] = value

    connection_string = settings.DATABASE_URL
    collection_name = "project_docs"
    embeddings = get_embeddings()

    chunks = []
    logs = {
        "step": "Project Retrieval",
        "filter": db_filter,
        "query": query,
        "project_id": project_id,
        "fetch_k": fetch_k,
        "top_k": top_k,
        "status": "success",
        "error": None,
        "retrieved_count": 0,
        "reranked_count": 0
    }

    try:
        docs = query_vector_store(
            connection_string=connection_string,
            collection_name=collection_name,
            embeddings=embeddings,
            query=query,
            k=fetch_k,
            filter=db_filter
        )

        raw_chunks = [
            RetrievalChunk(
                page_content=doc.page_content,
                metadata=doc.metadata
            )
            for doc in docs
        ]

        logs["retrieved_count"] = len(raw_chunks)

        reranker = QwenRerankerClient()
        ranked_chunks = reranker.rerank(query, raw_chunks, top_k=top_k)

        chunks = ranked_chunks
        logs["reranked_count"] = len(chunks)

    except Exception as e:
        logs["status"] = "failed"
        logs["error"] = str(e)

    return {
        "chunks": chunks,
        "logs": logs
    }
