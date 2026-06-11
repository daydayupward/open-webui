from typing import Dict, Any, Optional
from src.retrieval.base import BaseRetriever

class ProjectRetriever(BaseRetriever):
    collection_name = "project_docs"
    category_filter = "PROJECT"

    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        project_id = metadata.get("project_id")
        if not project_id:
            raise ValueError("project_id is required for project document retrieval")
            
        db_filter = {"category": self.category_filter, "project_id": project_id}
        
        for key, value in metadata.items():
            if key not in db_filter and value is not None:
                db_filter[key] = value
                
        return db_filter

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
    """
    if metadata is None:
        metadata = {}
    metadata["project_id"] = project_id
    
    retriever = ProjectRetriever()
    return retriever.retrieve(query, metadata, fetch_k, top_k)

async def aretrieve_project_docs(
    query: str,
    project_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    fetch_k: int = 10,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Retrieves project-specific documentation asynchronously using hard metadata filtering on
    category and project_id, followed by vector similarity search and reranking.
    """
    if metadata is None:
        metadata = {}
    metadata["project_id"] = project_id
    
    retriever = ProjectRetriever()
    return await retriever.aretrieve(query, metadata, fetch_k, top_k)
