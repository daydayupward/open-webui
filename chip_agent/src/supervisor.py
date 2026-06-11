import re
import json
import logging
from langchain_core.messages import SystemMessage
from src.utils import get_llm
from src.prompts.supervisor_prompt import SYSTEM_PROMPT
from src.metadata import QueryMetadata, normalize_metadata
from src.constants import ExpertRoute

logger = logging.getLogger(__name__)

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

async def arun_supervisor(messages: list) -> dict:
    llm = get_llm()
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    all_messages = [system_message] + messages
    
    route = ExpertRoute.FINALIZER
    metadata_dict = {
        "category": "General",
        "node": None,
        "tool": None,
        "project_id": None,
        "confidence": 1.0,
        "missing_fields": []
    }
    
    try:
        response = await llm.ainvoke(all_messages)
        content = response.content.strip()
        
        parsed = parse_json_safely(content)
        
        next_step = parsed.get("next", ExpertRoute.FINALIZER)
        if next_step == "FINISH":
            route = ExpertRoute.FINALIZER
        elif next_step in [ExpertRoute.PDK, ExpertRoute.EDA, ExpertRoute.METRICS, ExpertRoute.FINALIZER]:
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
        
    except Exception as e:
        logger.error("Supervisor routing failed: %s", e, exc_info=True)
        # Graceful fallback on any exception
        pass
        
    return {
        "route": route,
        "metadata": metadata_dict
    }
