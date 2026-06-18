from typing import Dict, Any, Optional
from src.retrieval.base import BaseRetriever

class ProjectRetriever(BaseRetriever):
    collection_name = "project_docs"
    category_filter = "Project_Doc"

    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        project_id = metadata.get("project_id")
        categories = metadata.get("categories", [])
        
        db_filter = {}
        if categories and "General" not in categories:
            db_cats = []
            for c in categories:
                if c == "Project":
                    db_cats.append("Project_Doc")
                else:
                    db_cats.append(c)
            db_filter["category"] = {"$in": db_cats}
        elif not categories:
            db_filter["category"] = {"$in": [self.category_filter]}
            
        if project_id:
            db_filter["project_id"] = project_id
        
        EXCLUDED_KEYS = {"confidence", "missing_fields", "categories"}
        for key, value in metadata.items():
            if key not in EXCLUDED_KEYS and key not in db_filter and value is not None:
                db_filter[key] = value
                
        return db_filter

def retrieve_project_docs(
    query: str,
    project_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    fetch_k: int = 10,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Retrieves project documentation using hard metadata filtering on
    category and optionally project_id, followed by vector similarity search and reranking.
    """
    if metadata is None:
        metadata = {}
    if project_id:
        metadata["project_id"] = project_id
    
    retriever = ProjectRetriever()
    return retriever.retrieve(query, metadata, fetch_k, top_k)

async def aretrieve_project_docs(
    query: str,
    project_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    fetch_k: int = 10,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Retrieves project documentation asynchronously using hard metadata filtering on
    category and optionally project_id, followed by vector similarity search and reranking.
    """
    if metadata is None:
        metadata = {}
    if project_id:
        metadata["project_id"] = project_id
    
    retriever = ProjectRetriever()
    return await retriever.aretrieve(query, metadata, fetch_k, top_k)
