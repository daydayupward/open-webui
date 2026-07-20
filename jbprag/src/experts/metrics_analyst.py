from src.state import AgentState
from src.experts.metrics_subgraph import build_metrics_subgraph


async def metrics_analyst_node(state: AgentState) -> dict:
    """
    Metrics Analyst node that delegates execution to the metrics subgraph,
    which performs routing, SQL generation, document retrieval, and summarization.
    """
    query = ""
    for msg in reversed(state.get("messages", [])):
        msg_type = getattr(msg, "type", None)
        if msg_type == "human" or msg.__class__.__name__ == "HumanMessage":
            query = msg.content
            break

    metadata = state.get("metadata", {})
    project_id = metadata.get("project_id", "")

    # Initialize the subgraph state
    sub_initial_state = {
        "messages": state.get("messages", []),
        "query": query,
        "metadata": metadata,
        "project_id": project_id,
        "query_type": "",
        "generated_sql": "",
        "sql_valid": False,
        "sql_error": "",
        "sql_results": [],
        "retrieved_docs": [],
        "tool_logs": [],
        "iterations": 0,
        "final_answer": "",
        "temperature": state.get("temperature", 0.0),
    }

    # Run the compiled subgraph
    subgraph = build_metrics_subgraph()
    sub_res = await subgraph.ainvoke(sub_initial_state)

    # Extract new messages generated inside the subgraph
    original_message_count = len(state.get("messages", []))
    new_messages = sub_res["messages"][original_message_count:]

    return {
        "messages": new_messages,
        "retrieved_docs": sub_res.get("retrieved_docs", []),
        "tool_logs": sub_res.get("tool_logs", []),
        "final_answer": sub_res.get("final_answer", ""),
    }
