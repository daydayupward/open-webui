import os
from typing import List, Dict, Any
from src.settings import settings
from src.utils import get_embeddings
from src.vector_store import query_vector_store
from src.retrieval.types import RetrievalChunk
from src.retrieval.reranker import QwenRerankerClient

def retrieve_pdk_rules(query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
    db_filter = {"category": "PDK"}
    node = metadata.get("node")
    if node:
        db_filter["node"] = node
        
    connection_string = settings.DATABASE_URL
    collection_name = "pdk_rules"
    embeddings = get_embeddings()
    
    chunks = []
    logs = {
        "step": "PDK Retrieval",
        "filter": db_filter,
        "query": query,
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
