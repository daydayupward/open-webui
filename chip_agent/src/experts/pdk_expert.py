from langchain_core.messages import SystemMessage
from src.state import AgentState
from src.utils import get_llm
from src.retrieval.pdk_retriever import retrieve_pdk_rules
from src.prompts.pdk_prompt import PDK_SYSTEM_PROMPT

def pdk_expert_node(state: AgentState) -> dict:
    query = ""
    for msg in reversed(state.get("messages", [])):
        msg_type = getattr(msg, "type", None)
        if msg_type == "human" or msg.__class__.__name__ == "HumanMessage":
            query = msg.content
            break
            
    metadata = state.get("metadata", {})
    retrieval_res = retrieve_pdk_rules(query, metadata)
    
    chunks = retrieval_res["chunks"]
    logs = retrieval_res["logs"]
    
    context = "\n\n".join([c.page_content for c in chunks])
    if not context:
        context = "No database context found due to connection issue or missing match."
        
    llm = get_llm()
    system_prompt = SystemMessage(
        content=PDK_SYSTEM_PROMPT.format(context=context)
    )
    
    messages = [system_prompt] + state["messages"]
    response = llm.invoke(messages)
    
    serializable_chunks = [c.model_dump() for c in chunks]
    
    return {
        "messages": [response],
        "retrieved_docs": serializable_chunks,
        "tool_logs": [logs]
    }
