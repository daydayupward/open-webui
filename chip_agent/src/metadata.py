from pydantic import BaseModel, Field
from typing import Optional, List

class QueryMetadata(BaseModel):
    categories: List[str] = Field(default_factory=list, description="List of categories for the query. Valid values: 'Project', 'EDA', 'PDK', 'IP', 'Training', 'Literature', 'Script', 'General'.")
    node: Optional[str] = Field(None, description="Process node (e.g. 'N5', 'N7', etc.)")
    tool: Optional[str] = Field(None, description="EDA tool name (e.g. 'Innovus', 'ICC2', 'Calibre', etc.)")
    project_id: Optional[str] = Field(None, description="Project ID (e.g. 'Proj_A', 'Proj_B', etc.)")
    confidence: float = Field(1.0, description="Confidence score between 0.0 and 1.0.")
    missing_fields: List[str] = Field(default_factory=list, description="Fields required but missing from query.")

def normalize_metadata(meta: QueryMetadata) -> QueryMetadata:
    if meta.categories:
        normalized_cats = []
        for cat in meta.categories:
            cat_clean = cat.strip().lower()
            if cat_clean in ["pdk", "process", "rule"]:
                normalized_cats.append("PDK")
            elif cat_clean in ["eda", "tool", "command"]:
                normalized_cats.append("EDA")
            elif cat_clean in ["project_doc", "project", "doc", "prd", "spec"]:
                normalized_cats.append("Project")
            elif cat_clean in ["ip", "ip_doc"]:
                normalized_cats.append("IP")
            elif cat_clean in ["training", "team"]:
                normalized_cats.append("Training")
            elif cat_clean in ["literature", "book", "paper"]:
                normalized_cats.append("Literature")
            elif cat_clean in ["script", "tcl", "python"]:
                normalized_cats.append("Script")
            elif cat_clean == "general":
                normalized_cats.append("General")
            else:
                normalized_cats.append(cat.strip().capitalize())
        # remove duplicates
        meta.categories = list(dict.fromkeys(normalized_cats))
            
    if meta.node:
        node_str = meta.node.strip().upper()
        if node_str in ["N5", "5NM", "5"]:
            meta.node = "N5"
        elif node_str in ["N7", "7NM", "7"]:
            meta.node = "N7"
        else:
            meta.node = node_str
            
    if meta.tool:
        tool_str = meta.tool.strip().lower()
        if tool_str in ["innovus", "encounter"]:
            meta.tool = "Innovus"
        elif tool_str in ["icc2", "icc", "ic compiler"]:
            meta.tool = "ICC2"
        elif tool_str == "calibre":
            meta.tool = "Calibre"
        elif tool_str in ["primetime", "pt"]:
            meta.tool = "PrimeTime"
        else:
            meta.tool = meta.tool.strip().capitalize()
            
    if meta.project_id:
        proj_str = meta.project_id.strip().lower().replace("_", "").replace("-", "").replace(" ", "")
        if "proja" in proj_str or "projecta" in proj_str:
            meta.project_id = "Proj_A"
        elif "projb" in proj_str or "projectb" in proj_str:
            meta.project_id = "Proj_B"
        else:
            meta.project_id = meta.project_id.strip()
            
    return meta
