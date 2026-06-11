import operator
from typing import TypedDict, List, Annotated, Dict, Any
from langchain_core.messages import AnyMessage

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    route: str
    metadata: Dict[str, Any]
    retrieved_docs: Annotated[List[Dict[str, Any]], operator.add]
    tool_logs: Annotated[List[Dict[str, Any]], operator.add]
    final_answer: str
    errors: Annotated[List[str], operator.add]
    request_id: str
    temperature: float
