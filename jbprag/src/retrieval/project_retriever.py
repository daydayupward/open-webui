from typing import Dict, Any, Optional
from src.retrieval.base import BaseRetriever

class ProjectRetriever(BaseRetriever):
    _default_collection_name = "project_docs"
    category_filter = "Project_Doc"

    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        project_id = metadata.get("project_id")
        categories = metadata.get("categories", [])
        
        db_filter = {}
        db_cats = []
        if categories and "General" not in categories:
            for c in categories:
                if c == "Project":
                    db_cats.append("Project_Doc")
                else:
                    db_cats.append(c)
            
            # If the categories only contain project-independent ones, include project/platform docs
            if "Project_Doc" not in db_cats and "Platform_Flow" not in db_cats:
                db_cats.extend(["Platform_Flow", "Project_Doc"])
                
            db_filter["category"] = {"$in": db_cats}
        elif not categories:
            db_cats = [self.category_filter]
            db_filter["category"] = {"$in": db_cats}
            
        # Only filter by project_id if the query targets project-specific docs (Project_Doc)
        if project_id and db_cats == ["Project_Doc"]:
            db_filter["project_id"] = project_id
        
        EXCLUDED_KEYS = {"confidence", "missing_fields", "categories", "project_id"}
        for key, value in metadata.items():
            if key not in EXCLUDED_KEYS and key not in db_filter and value is not None:
                db_filter[key] = value
                
        return db_filter

def retrieve_project_docs(
    query: str,
    project_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    fetch_k: int = 50,
    top_k: int = 10
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
    fetch_k: int = 50,
    top_k: int = 10
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
