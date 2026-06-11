from typing import Dict, Any
from src.retrieval.base import BaseRetriever

class PDKRetriever(BaseRetriever):
    collection_name = "pdk_rules"
    category_filter = "PDK"

    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        db_filter = {"category": self.category_filter}
        node = metadata.get("node")
        if node:
            db_filter["node"] = node
        return db_filter

def retrieve_pdk_rules(query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
    retriever = PDKRetriever()
    return retriever.retrieve(query, metadata, fetch_k, top_k)

async def aretrieve_pdk_rules(query: str, metadata: Dict[str, Any], fetch_k: int = 10, top_k: int = 3) -> Dict[str, Any]:
    retriever = PDKRetriever()
    return await retriever.aretrieve(query, metadata, fetch_k, top_k)
