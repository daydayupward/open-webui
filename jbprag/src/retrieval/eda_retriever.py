from typing import Dict, Any
from src.retrieval.base import BaseRetriever

class EDARetriever(BaseRetriever):
    _default_collection_name = "eda_manuals"
    category_filter = "EDA"

    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        categories = metadata.get("categories", [])
        if not categories:
            categories = [self.category_filter]
            
        db_filter = {"category": {"$in": categories}}
        tool = metadata.get("tool")
        if tool:
            from src.ingestion.metadata_mapper import VALID_TOOLS
            other_tools = [t for t in VALID_TOOLS if t.lower() != tool.lower()]
            db_filter["tool"] = {"$nin": other_tools}
            
        EXCLUDED_KEYS = {"confidence", "missing_fields", "categories"}
        for key, value in metadata.items():
            if key not in EXCLUDED_KEYS and key not in db_filter and value is not None:
                db_filter[key] = value
                
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
