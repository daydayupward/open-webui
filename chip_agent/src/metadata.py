from pydantic import BaseModel, Field
from typing import Optional, List

class QueryMetadata(BaseModel):
    category: Optional[str] = Field(None, description="The category of the query: 'PDK', 'EDA', 'Project_Doc', or 'General'.")
    node: Optional[str] = Field(None, description="Process node (e.g. 'N5', 'N7', etc.)")
    tool: Optional[str] = Field(None, description="EDA tool name (e.g. 'Innovus', 'ICC2', 'Calibre', etc.)")
    project_id: Optional[str] = Field(None, description="Project ID (e.g. 'Proj_A', 'Proj_B', etc.)")
    confidence: float = Field(1.0, description="Confidence score between 0.0 and 1.0.")
    missing_fields: List[str] = Field(default_factory=list, description="Fields required but missing from query.")

def normalize_metadata(meta: QueryMetadata) -> QueryMetadata:
    if meta.category:
        cat = meta.category.strip().lower()
        if cat in ["pdk", "process"]:
            meta.category = "PDK"
        elif cat in ["eda", "tool"]:
            meta.category = "EDA"
        elif cat in ["project_doc", "project", "doc"]:
            meta.category = "Project_Doc"
        elif cat == "general":
            meta.category = "General"
            
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
