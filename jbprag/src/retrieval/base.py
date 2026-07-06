from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from src.settings import settings
from src.utils import get_embeddings
from src.vector_store import query_vector_store
from src.retrieval.types import RetrievalChunk
from src.retrieval.reranker import QwenRerankerClient

class BaseRetriever(ABC):
    _default_collection_name: str
    category_filter: str
    
    @property
    def collection_name(self) -> str:
        from src.admin_db import get_config
        config_key = f"{self._default_collection_name}_collection"
        try:
            return get_config().get(config_key, self._default_collection_name)
        except Exception:
            return self._default_collection_name
    
    def retrieve(self, query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
        # Query Expansion for common abbreviations
        import re
        expanded_query = query
        abbrevs = {
            r'\bsta\b': 'STA (Static Timing Analysis)',
            r'\bdrc\b': 'DRC (Design Rule Check)',
            r'\blvs\b': 'LVS (Layout Versus Schematic)',
            r'\bpdk\b': 'PDK (Process Design Kit)',
            r'\beda\b': 'EDA (Electronic Design Automation)'
        }
        for pattern, replacement in abbrevs.items():
            if re.search(pattern, query, re.IGNORECASE):
                explanation = replacement.split('(')[1].rstrip(')').lower()
                if explanation not in query.lower():
                    expanded_query = re.sub(pattern, replacement, expanded_query, flags=re.IGNORECASE)

        db_filter = self._build_filter(metadata)
        
        connection_string = settings.DATABASE_URL
        embeddings = get_embeddings()
        
        chunks = []
        logs = {
            "step": f"{self.category_filter} Retrieval",
            "filter": db_filter,
            "query": expanded_query,
            "original_query": query,
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
                collection_name=self.collection_name,
                embeddings=embeddings,
                query=expanded_query,
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
        
    async def aretrieve(self, query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
        # Query Expansion for common abbreviations
        import re
        expanded_query = query
        abbrevs = {
            r'\bsta\b': 'STA (Static Timing Analysis)',
            r'\bdrc\b': 'DRC (Design Rule Check)',
            r'\blvs\b': 'LVS (Layout Versus Schematic)',
            r'\bpdk\b': 'PDK (Process Design Kit)',
            r'\beda\b': 'EDA (Electronic Design Automation)'
        }
        for pattern, replacement in abbrevs.items():
            if re.search(pattern, query, re.IGNORECASE):
                explanation = replacement.split('(')[1].rstrip(')').lower()
                if explanation not in query.lower():
                    expanded_query = re.sub(pattern, replacement, expanded_query, flags=re.IGNORECASE)

        from src.vector_store import aquery_vector_store
        db_filter = self._build_filter(metadata)
        
        connection_string = settings.DATABASE_URL
        embeddings = get_embeddings()
        
        chunks = []
        logs = {
            "step": f"{self.category_filter} Retrieval",
            "filter": db_filter,
            "query": expanded_query,
            "original_query": query,
            "fetch_k": fetch_k,
            "top_k": top_k,
            "status": "success",
            "error": None,
            "retrieved_count": 0,
            "reranked_count": 0
        }
        
        try:
            docs = await aquery_vector_store(
                connection_string=connection_string,
                collection_name=self.collection_name,
                embeddings=embeddings,
                query=expanded_query,
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
        
    @abstractmethod
    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        pass
