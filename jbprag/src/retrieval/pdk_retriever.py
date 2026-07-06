from typing import Dict, Any
from src.retrieval.base import BaseRetriever

class PDKRetriever(BaseRetriever):
    _default_collection_name = "pdk_rules"
    category_filter = "PDK"

    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        categories = metadata.get("categories", [])
        if not categories:
            categories = [self.category_filter]
            
        db_filter = {"category": {"$in": categories}}
        node = metadata.get("node")
        if node:
            db_filter["node"] = node
            
        EXCLUDED_KEYS = {"confidence", "missing_fields", "categories"}
        for key, value in metadata.items():
            if key not in EXCLUDED_KEYS and key not in db_filter and value is not None:
                db_filter[key] = value
                
        return db_filter

def retrieve_pdk_rules(query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
    retriever = PDKRetriever()
    return retriever.retrieve(query, metadata, fetch_k, top_k)

async def aretrieve_pdk_rules(query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
    retriever = PDKRetriever()
    return await retriever.aretrieve(query, metadata, fetch_k, top_k)
