from src.state import AgentState
from src.experts.eda_script_subgraph import build_eda_subgraph

async def eda_script_expert_node(state: AgentState) -> dict:
    """
    EDA Script Expert node that delegates execution to the EDA script subgraph,
    which performs a retrieve-generate-lint-refine loop.
    """
    query = ""
    for msg in reversed(state.get("messages", [])):
        msg_type = getattr(msg, "type", None)
        if msg_type == "human" or msg.__class__.__name__ == "HumanMessage":
            query = msg.content
            break
            
    # Initialize the subgraph state
    sub_initial_state = {
        "messages": state.get("messages", []),
        "query": query,
        "metadata": state.get("metadata", {}),
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "linter_result": {},
        "previous_response": "",
        "final_answer": "",
        "temperature": state.get("temperature", 0.0)
    }
    
    # Run the compiled subgraph
    subgraph = build_eda_subgraph()
    sub_res = await subgraph.ainvoke(sub_initial_state)
    
    # Extract new messages generated inside the subgraph
    original_message_count = len(state.get("messages", []))
    new_messages = sub_res["messages"][original_message_count:]
    
    return {
        "messages": new_messages,
        "retrieved_docs": sub_res.get("retrieved_docs", []),
        "tool_logs": sub_res.get("tool_logs", []),
        "final_answer": sub_res.get("final_answer", "")
    }
