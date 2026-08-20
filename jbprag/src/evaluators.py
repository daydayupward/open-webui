import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils import get_llm
from src.supervisor import parse_json_safely

logger = logging.getLogger(__name__)

DOC_GRADER_PROMPT = """You are a grader assessing relevance of a retrieved document to a user question.
If the document contains key terms, rules, or concepts related to the user question, grade it as relevant.
It does not need to be a perfect answer, just relevant to the topic of the query.

Input Document:
{document}

User Question:
{query}

Output your decision strictly as a JSON object:
{{
  "binary_score": "yes" or "no"
}}
"""

HALLUCINATION_GRADER_PROMPT = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved documents.
Check if the generation contains facts, values, or claims that contradict or are not present in the retrieved documents.
If the generation is fully supported by the documents (no hallucinated claims), grade it as grounded ("yes"). Otherwise, grade it as not grounded ("no").

Retrieved Documents:
{documents}

LLM Generation:
{generation}

Output your decision strictly as a JSON object:
{{
  "binary_score": "yes" or "no"
}}
"""

ANSWER_GRADER_PROMPT = """You are a grader assessing whether a generated answer fully addresses and resolves the user's question.
If the answer directly answers the core question and is complete, grade it as "yes". If it is incomplete, vague, or does not answer the question, grade it as "no".

User Question:
{query}

Generated Answer:
{generation}

Output your decision strictly as a JSON object:
{{
  "binary_score": "yes" or "no"
}}
"""

QUERY_REWRITER_PROMPT = """You are a query rewriter that optimizes a search query for vector database retrieval.
Analyze the user's original query and rewrite it to be more search-friendly, focusing on technical terms, layer names, and DRC rule codes (like M1.SP.1).
Do not include conversational filler.

Original Query:
{query}

Output your decision strictly as a JSON object:
{{
  "rewritten_query": "string"
}}
"""

async def grade_document_relevance(doc_text: str, query: str) -> bool:
    """Assess if a document is relevant to a query."""
    llm = get_llm(temperature=0.0)
    messages = [
        SystemMessage(content="You are a strict relevance grader. Output only JSON."),
        HumanMessage(content=DOC_GRADER_PROMPT.format(document=doc_text, query=query))
    ]
    try:
        response = await llm.ainvoke(messages, config={"tags": ["evaluator"]})
        parsed = parse_json_safely(response.content)
        score = parsed.get("binary_score", "no").strip().lower()
        logger.info("[Self-RAG Doc Grader] Document graded as relevant: %s", score == "yes")
        return score == "yes"
    except Exception as e:
        logger.error("Doc grader failed: %s", e)
        return False # Default to False on failure — reject on error to prevent hallucination

async def grade_hallucination(generation: str, docs: list) -> bool:
    """Assess if the generated answer is grounded in retrieved documents."""
    llm = get_llm(temperature=0.0)
    docs_text = "\n\n".join([d.page_content if hasattr(d, 'page_content') else str(d) for d in docs])
    messages = [
        SystemMessage(content="You are a strict hallucination checker. Output only JSON."),
        HumanMessage(content=HALLUCINATION_GRADER_PROMPT.format(documents=docs_text, generation=generation))
    ]
    try:
        response = await llm.ainvoke(messages, config={"tags": ["evaluator"]})
        parsed = parse_json_safely(response.content)
        score = parsed.get("binary_score", "no").strip().lower()
        logger.info("[Self-RAG Hallucination Grader] Grounded: %s", score == "yes")
        return score == "yes"
    except Exception as e:
        logger.error("Hallucination grader failed: %s", e)
        return False # Default to False on failure — reject on error to prevent hallucination

async def grade_answer_completeness(generation: str, query: str) -> bool:
    """Assess if the generated answer addresses the query."""
    llm = get_llm(temperature=0.0)
    messages = [
        SystemMessage(content="You are a strict answer quality grader. Output only JSON."),
        HumanMessage(content=ANSWER_GRADER_PROMPT.format(query=query, generation=generation))
    ]
    try:
        response = await llm.ainvoke(messages, config={"tags": ["evaluator"]})
        parsed = parse_json_safely(response.content)
        score = parsed.get("binary_score", "no").strip().lower()
        logger.info("[Self-RAG Answer Grader] Completeness grade: %s", score == "yes")
        return score == "yes"
    except Exception as e:
        logger.error("Answer grader failed: %s", e)
        return False # Default to False on failure — reject on error to prevent hallucination

async def rewrite_query(query: str) -> str:
    """Rewrite query to optimize RAG retrieval."""
    llm = get_llm(temperature=0.0)
    messages = [
        SystemMessage(content="You are a technical query optimizer. Output only JSON."),
        HumanMessage(content=QUERY_REWRITER_PROMPT.format(query=query))
    ]
    try:
        response = await llm.ainvoke(messages, config={"tags": ["evaluator"]})
        parsed = parse_json_safely(response.content)
        rewritten = parsed.get("rewritten_query", query)
        logger.info("[Self-RAG Query Rewriter] Rewrote '%s' -> '%s'", query, rewritten)
        return rewritten
    except Exception as e:
        logger.error("Query rewriter failed: %s", e)
        return query
