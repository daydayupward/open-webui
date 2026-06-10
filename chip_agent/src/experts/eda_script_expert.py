from typing import TypedDict, List
from langchain_core.messages import AnyMessage, SystemMessage
from src.utils import get_llm

class AgentState(TypedDict):
    messages: List[AnyMessage]

def eda_script_expert_node(state: AgentState) -> dict:
    llm = get_llm()
    system_prompt = SystemMessage(
        content="You are a specialized EDA Script Expert for backend chip physical design. "
                "Your focus is tool commands and Tcl/Skill script generation for Innovus, ICC2, Calibre, etc. "
                "Output clear scripts, tool usage instructions, and explanation."
    )
    messages = [system_prompt] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}
