from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class RetrievalChunk(BaseModel):
    page_content: str
    metadata: Dict[str, Any]
    score: Optional[float] = None

class RetrievalRequest(BaseModel):
    query: str
    filter: Optional[Dict[str, Any]] = None
    top_k: int = 5

class RetrievalResult(BaseModel):
    chunks: List[RetrievalChunk]
