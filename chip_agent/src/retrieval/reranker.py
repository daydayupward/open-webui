import httpx
from typing import List
from src.settings import settings
from src.retrieval.types import RetrievalChunk

class QwenRerankerClient:
    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        self.base_url = base_url or settings.rerank_base_url
        self.api_key = api_key or settings.rerank_api_key
        self.model = model or settings.RERANK_MODEL

    def rerank(self, query: str, chunks: List[RetrievalChunk], top_k: int = 5) -> List[RetrievalChunk]:
        if not chunks:
            return []
            
        url = self.base_url.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        url = f"{url}/rerank"
        
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        payload = {
            "model": self.model,
            "query": query,
            "documents": [c.page_content for c in chunks],
            "top_n": top_k
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results") if isinstance(data, dict) else data
                    if results:
                        ranked_chunks = []
                        for item in results:
                            idx = item.get("index")
                            score = item.get("score", 0.0)
                            if idx is not None and idx < len(chunks):
                                chunk = chunks[idx]
                                chunk.score = score
                                ranked_chunks.append(chunk)
                        return ranked_chunks[:top_k]
        except Exception as e:
            # Fallback
            pass
            
        return IdentityReranker().rerank(query, chunks, top_k)

class IdentityReranker:
    def rerank(self, query: str, chunks: List[RetrievalChunk], top_k: int = 5) -> List[RetrievalChunk]:
        result = []
        for i, c in enumerate(chunks[:top_k]):
            c.score = 1.0 - (i * 0.1)
            result.append(c)
        return result
