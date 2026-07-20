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
    from langchain_core.messages import AIMessage
    cleaned_messages = []
    for m in messages:
        if m.type == "human":
            cleaned_messages.append(m)
        elif m.type == "ai":
            stripped = m.content.strip()
            if stripped.startswith("{") or "{" in stripped:
                cleaned_messages.append(m)
            else:
                cleaned_messages.append(AIMessage(content="[Answered by expert node]"))
                
    all_messages = [system_message] + cleaned_messages
    
    # Debug log the messages
    logger.info("Supervisor incoming messages: %s", [str(m) for m in all_messages])
    
    route = ExpertRoute.FINALIZER
    metadata_dict = {
        "categories": ["Literature"],
        "vendor": None,
        "node": None,
        "tool": None,
        "project_id": None,
        "confidence": 1.0,
        "missing_fields": []
    }
    
    content = ""
    try:
        response = await llm.ainvoke(all_messages, config={"tags": ["evaluator"]})
        content = response.content.strip()
        
        parsed = parse_json_safely(content)
        
        next_step = parsed.get("next", ExpertRoute.FINALIZER)
        if next_step == "FINISH":
            route = ExpertRoute.FINALIZER
        elif next_step in [ExpertRoute.PDK, ExpertRoute.EDA, ExpertRoute.METRICS, ExpertRoute.FINALIZER]:
            route = next_step
            
        raw_meta = parsed.get("metadata", {})
        cats = raw_meta.get("categories")
        if not cats and raw_meta.get("category"):
            cats = [raw_meta.get("category")]
        elif not cats:
            cats = []
            
        query_meta = QueryMetadata(
            categories=cats,
            vendor=raw_meta.get("vendor"),
            node=raw_meta.get("node"),
            tool=raw_meta.get("tool"),
            project_id=raw_meta.get("project_id"),
            confidence=raw_meta.get("confidence", 1.0),
            missing_fields=raw_meta.get("missing_fields", [])
        )
        
        normalized_meta = normalize_metadata(query_meta)
        metadata_dict = normalized_meta.model_dump()
        
        return {
            "route": route,
            "metadata": metadata_dict
        }
        
    except Exception as e:
        logger.error("Supervisor routing failed: %s", e, exc_info=True)
        if content:
            from langchain_core.messages import AIMessage
            return {
                "route": ExpertRoute.FINALIZER,
                "metadata": metadata_dict,
                "messages": [AIMessage(content=content)]
            }
        
        return {
            "route": route,
            "metadata": metadata_dict
        }
