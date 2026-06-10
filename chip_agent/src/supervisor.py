import re
import json
from langchain_core.messages import SystemMessage
from src.utils import get_llm
from src.prompts.supervisor_prompt import SYSTEM_PROMPT
from src.metadata import QueryMetadata, normalize_metadata

def parse_json_safely(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
        
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
            
    match_braces = re.search(r"(\{.*\})", text, re.DOTALL)
    if match_braces:
        try:
            return json.loads(match_braces.group(1))
        except Exception:
            pass
            
    raise ValueError(f"Could not parse valid JSON from text: {text}")

def run_supervisor(messages: list) -> dict:
    llm = get_llm()
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    all_messages = [system_message] + messages
    
    route = "finalizer"
    metadata_dict = {
        "category": "General",
        "node": None,
        "tool": None,
        "project_id": None,
        "confidence": 1.0,
        "missing_fields": []
    }
    
    try:
        response = llm.invoke(all_messages)
        content = response.content.strip()
        
        parsed = parse_json_safely(content)
        
        next_step = parsed.get("next", "finalizer")
        if next_step == "FINISH":
            route = "finalizer"
        elif next_step in ["pdk_expert", "eda_script_expert", "metrics_analyst", "finalizer"]:
            route = next_step
            
        raw_meta = parsed.get("metadata", {})
        query_meta = QueryMetadata(
            category=raw_meta.get("category"),
            node=raw_meta.get("node"),
            tool=raw_meta.get("tool"),
            project_id=raw_meta.get("project_id"),
            confidence=raw_meta.get("confidence", 1.0),
            missing_fields=raw_meta.get("missing_fields", [])
        )
        
        normalized_meta = normalize_metadata(query_meta)
        metadata_dict = normalized_meta.model_dump()
        
    except Exception:
        # Graceful fallback on any exception
        pass
        
    return {
        "route": route,
        "metadata": metadata_dict
    }
