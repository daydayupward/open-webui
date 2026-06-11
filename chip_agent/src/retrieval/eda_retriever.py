from typing import Dict, Any
from src.retrieval.base import BaseRetriever

class EDARetriever(BaseRetriever):
    collection_name = "eda_manuals"
    category_filter = "EDA"

    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        db_filter = {"category": self.category_filter}
        tool = metadata.get("tool")
        if tool:
            db_filter["tool"] = tool
        return db_filter

def retrieve_eda_manuals(query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
    """
    Retrieves EDA reference documents using hard metadata filtering on tool and category,
    followed by vector similarity search and reranking.
    """
    retriever = EDARetriever()
    return retriever.retrieve(query, metadata, fetch_k, top_k)

async def aretrieve_eda_manuals(query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
    """
    Retrieves EDA reference documents asynchronously using hard metadata filtering on tool and category,
    followed by vector similarity search and reranking.
    """
    retriever = EDARetriever()
    return await retriever.aretrieve(query, metadata, fetch_k, top_k)
