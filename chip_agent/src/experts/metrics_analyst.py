from typing import TypedDict, List
from langchain_core.messages import AnyMessage, SystemMessage
from src.utils import get_llm

class AgentState(TypedDict):
    messages: List[AnyMessage]

def metrics_analyst_node(state: AgentState) -> dict:
    llm = get_llm()
    system_prompt = SystemMessage(
        content="You are a specialized Metrics & History Analyst for backend chip physical design. "
                "Your focus is project-specific metrics (PPA, timing convergence, timing reports) and historical project documentation. "
                "Output timing analysis, timing convergence reports, and project timing details based on the context."
    )
    messages = [system_prompt] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}
