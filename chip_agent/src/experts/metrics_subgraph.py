"""
Metrics Subgraph: route -> generate sql -> validate -> execute -> doc rag -> summarize

An agentic loop that:
1. Routes queries to either SQL or document retrieval paths (or both)
2. For SQL: generates SQL from natural language, validates it, executes it
3. Retrieves relevant project documents
4. Summarizes results
"""

import operator
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage

from src.utils import get_llm
from src.sql.sql_client import aexecute_read_query
from src.sql.sql_guardrails import validate_sql_query
from src.retrieval.project_retriever import aretrieve_project_docs
from src.prompts.metrics_prompt import (
    TEXT_TO_SQL_SYSTEM_PROMPT,
    TEXT_TO_SQL_USER_TEMPLATE,
    RESULT_SUMMARY_SYSTEM_PROMPT,
    RESULT_SUMMARY_USER_TEMPLATE,
)

# Database schema for the text-to-SQL prompt
DB_SCHEMA = """CREATE TABLE project_metrics (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(50) NOT NULL,
    metric_date DATE NOT NULL,
    wns FLOAT NOT NULL,
    tns FLOAT NOT NULL,
    power FLOAT NOT NULL,
    area FLOAT NOT NULL
);"""

MAX_SQL_RETRIES = 2


class MetricsSubgraphState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    query: str
    metadata: Dict[str, Any]
    project_id: str
    query_type: str  # "sql", "docs", "both"
    generated_sql: str
    sql_valid: bool
    sql_error: str
    sql_results: List[Dict[str, Any]]
    retrieved_docs: Annotated[List[Dict[str, Any]], operator.add]
    tool_logs: Annotated[List[Dict[str, Any]], operator.add]
    iterations: int
    final_answer: str
    temperature: float


async def route_node(state: MetricsSubgraphState) -> dict:
    """Determine if the query needs SQL, doc retrieval, or both."""
    query = state.get("query", "")
    project_id = state.get("project_id", "")

    log_entry: Dict[str, Any] = {
        "step": "Route",
        "query": query,
        "project_id": project_id,
    }

    if not project_id:
        return {
            "query_type": "clarify",
            "tool_logs": [{**log_entry, "routed_to": "clarify", "reason": "Missing project_id"}],
        }

    # Use LLM to classify the query type
    llm = get_llm(state.get("temperature", 0.0))
    classification_prompt = SystemMessage(
        content=(
            "You are a query classifier for a chip design metrics system. "
            "Classify the user query into exactly one category:\n"
            "- 'sql': The query asks about numerical metrics, trends, comparisons, "
            "aggregations, or data that can be answered from a database table.\n"
            "- 'docs': The query asks about documentation, methodology, explanations, "
            "or context that requires reading project documents.\n"
            "- 'both': The query requires both database metrics and document context.\n\n"
            "Respond with ONLY one word: sql, docs, or both."
        )
    )
    response = await llm.ainvoke([classification_prompt, HumanMessage(content=query)])
    raw_type = response.content.strip().lower()

    # Normalize to valid types
    if raw_type in ("sql", "docs", "both"):
        query_type = raw_type
    else:
        query_type = "both"  # Default to both if classification is unclear

    return {
        "query_type": query_type,
        "tool_logs": [{**log_entry, "routed_to": query_type}],
    }


async def generate_sql_node(state: MetricsSubgraphState) -> dict:
    """Use LLM to generate SQL from natural language."""
    query = state.get("query", "")
    llm = get_llm(state.get("temperature", 0.0))

    system_prompt = SystemMessage(
        content=TEXT_TO_SQL_SYSTEM_PROMPT.format(schema=DB_SCHEMA)
    )
    user_prompt = HumanMessage(
        content=TEXT_TO_SQL_USER_TEMPLATE.format(
            question=query, 
            project_id=state.get("project_id", "")
        )
    )

    response = await llm.ainvoke([system_prompt, user_prompt])
    generated_sql = response.content.strip()

    # Clean up markdown fences if present
    if generated_sql.startswith("```"):
        lines = generated_sql.split("\n")
        # Remove first and last lines (fences)
        sql_lines = [l for l in lines if not l.strip().startswith("```")]
        generated_sql = "\n".join(sql_lines).strip()

    current_iterations = state.get("iterations", 0) + 1

    return {
        "generated_sql": generated_sql,
        "iterations": current_iterations,
        "tool_logs": [
            {
                "step": f"Generate SQL (Iteration {current_iterations})",
                "generated_sql": generated_sql,
            }
        ],
    }


async def validate_sql_node(state: MetricsSubgraphState) -> dict:
    """Use sql_guardrails to validate generated SQL."""
    generated_sql = state.get("generated_sql", "")
    is_valid = validate_sql_query(generated_sql)

    sql_error = ""
    if not is_valid:
        sql_error = "SQL validation failed: query must be a SELECT statement using only allowlisted tables."

    log_entry = {
        "step": "Validate SQL",
        "generated_sql": generated_sql,
        "valid": is_valid,
        "error": sql_error,
    }

    return {
        "sql_valid": is_valid,
        "sql_error": sql_error,
        "tool_logs": [log_entry],
    }


async def execute_sql_node(state: MetricsSubgraphState) -> dict:
    """Execute validated SQL using sql_client."""
    generated_sql = state.get("generated_sql", "")
    project_id = state.get("project_id", "")

    try:
        results = await aexecute_read_query(generated_sql)

        return {
            "sql_results": results,
            "tool_logs": [
                {
                    "step": "Execute SQL",
                    "executed_sql": generated_sql,
                    "row_count": len(results),
                    "status": "success",
                }
            ],
        }
    except Exception as e:
        return {
            "sql_results": [],
            "tool_logs": [
                {
                    "step": "Execute SQL",
                    "executed_sql": generated_sql,
                    "status": "error",
                    "error": str(e),
                }
            ],
        }


async def retrieve_docs_node(state: MetricsSubgraphState) -> dict:
    """Retrieve project documents using project_retriever."""
    query = state.get("query", "")
    project_id = state.get("project_id", "")

    retrieval_res = await aretrieve_project_docs(query, project_id)

    chunks_data = [
        {"content": chunk.page_content, "metadata": chunk.metadata}
        for chunk in retrieval_res["chunks"]
    ]

    return {
        "retrieved_docs": chunks_data,
        "tool_logs": [retrieval_res["logs"]],
    }


async def summarize_node(state: MetricsSubgraphState) -> dict:
    """Use LLM to summarize results from SQL and/or document retrieval."""
    query = state.get("query", "")
    sql_results = state.get("sql_results", [])
    retrieved_docs = state.get("retrieved_docs", [])

    llm = get_llm(state.get("temperature", 0.0))

    # Build context parts
    context_parts = []

    if sql_results:
        results_str = str(sql_results)
        context_parts.append(
            f"SQL Query Results:\n{results_str}"
        )

    if retrieved_docs:
        docs_str = "\n\n".join(
            f"Document Chunk:\n{doc['content']}" for doc in retrieved_docs
        )
        context_parts.append(f"Retrieved Documents:\n{docs_str}")

    if not context_parts:
        context_str = "No data or documents were retrieved."
    else:
        context_str = "\n\n".join(context_parts)

    system_prompt = SystemMessage(content=RESULT_SUMMARY_SYSTEM_PROMPT)
    user_prompt = HumanMessage(
        content=RESULT_SUMMARY_USER_TEMPLATE.format(
            question=query,
            results=context_str,
        )
    )

    response = await llm.ainvoke([system_prompt, user_prompt])

    return {
        "final_answer": response.content,
        "messages": [response],
        "tool_logs": [
            {
                "step": "Summarize",
                "has_sql_results": bool(sql_results),
                "has_doc_results": bool(retrieved_docs),
            }
        ],
    }


def clarify_node(state: MetricsSubgraphState) -> dict:
    """Handle the case where project_id is missing."""
    return {
        "final_answer": (
            "I need a project ID to look up metrics or project documents. "
            "Please provide the project ID you'd like me to query."
        ),
        "tool_logs": [
            {
                "step": "Clarify",
                "reason": "Missing project_id",
            }
        ],
    }


# --- Conditional routing functions ---

def route_after_classify(state: MetricsSubgraphState) -> str:
    """Route based on the query classification."""
    query_type = state.get("query_type", "both")
    if query_type == "clarify":
        return "clarify"
    if query_type == "sql":
        return "generate_sql"
    if query_type == "docs":
        return "retrieve_docs"
    # "both" -> start with SQL generation (docs retrieval happens in parallel via a separate path)
    return "generate_sql"


def route_after_validate(state: MetricsSubgraphState) -> str:
    """Route based on SQL validation result."""
    if state.get("sql_valid", False):
        return "execute_sql"
    iterations = state.get("iterations", 0)
    if iterations < MAX_SQL_RETRIES:
        return "generate_sql"  # Retry SQL generation
    # Exhausted retries: fall through to docs-only path
    return "retrieve_docs"


def route_after_sql(state: MetricsSubgraphState) -> str:
    """After SQL execution, decide if we also need doc retrieval."""
    query_type = state.get("query_type", "both")
    if query_type == "both":
        return "retrieve_docs"
    return "summarize"


def build_metrics_subgraph():
    """Build and compile the metrics subgraph."""
    workflow = StateGraph(MetricsSubgraphState)

    # Add nodes
    workflow.add_node("route", route_node)
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("validate_sql", validate_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("retrieve_docs", retrieve_docs_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("clarify", clarify_node)

    # Entry point
    workflow.set_entry_point("route")

    # Route -> conditional
    workflow.add_conditional_edges(
        "route",
        route_after_classify,
        {
            "clarify": "clarify",
            "generate_sql": "generate_sql",
            "retrieve_docs": "retrieve_docs",
        },
    )

    # SQL pipeline
    workflow.add_edge("generate_sql", "validate_sql")

    workflow.add_conditional_edges(
        "validate_sql",
        route_after_validate,
        {
            "execute_sql": "execute_sql",
            "generate_sql": "generate_sql",
            "retrieve_docs": "retrieve_docs",
        },
    )

    workflow.add_conditional_edges(
        "execute_sql",
        route_after_sql,
        {
            "retrieve_docs": "retrieve_docs",
            "summarize": "summarize",
        },
    )

    # Docs -> summarize
    workflow.add_edge("retrieve_docs", "summarize")

    # Terminal nodes
    workflow.add_edge("summarize", END)
    workflow.add_edge("clarify", END)

    return workflow.compile()
