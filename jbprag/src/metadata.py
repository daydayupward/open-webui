from pydantic import BaseModel, Field
from typing import Optional, List

class QueryMetadata(BaseModel):
    categories: List[str] = Field(default_factory=list, description="List of categories for the query. Valid values: 'PDK', 'StdCell', 'SRAM', 'IP', 'EDA', 'Platform_Flow', 'Project_Doc', 'Script', 'Literature'.")
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
            if cat_clean in ["pdk", "process", "rule", "foundry", "foundry_doc", "foundry_manual"]:
                normalized_cats.append("PDK")
            elif cat_clean in ["stdcell", "standard_cell", "liberty", "lib"]:
                normalized_cats.append("StdCell")
            elif cat_clean in ["sram", "memory", "macro"]:
                normalized_cats.append("SRAM")
            elif cat_clean in ["platform", "flow", "methodology", "platform_flow", "checklist_template", "signoff_template"]:
                normalized_cats.append("Platform_Flow")
            elif cat_clean in ["script", "tcl", "python", "makefile", "csh", "sh"]:
                normalized_cats.append("Script")
            elif cat_clean in ["literature", "paper", "book", "textbook", "general", "training", "team"]:
                normalized_cats.append("Literature")
            elif cat_clean in ["project_doc", "project", "doc", "checklist_result", "project_checklist", "prd", "spec"]:
                normalized_cats.append("Project_Doc")
            elif cat_clean in ["ip", "ip_doc", "datasheet", "manual"]:
                normalized_cats.append("IP")
            elif cat_clean in ["eda", "tool", "command"]:
                normalized_cats.append("EDA")
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
        elif proj_str == "jbp":
            meta.project_id = None
        else:
            meta.project_id = meta.project_id.strip()
            
    return meta
