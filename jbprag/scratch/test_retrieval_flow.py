import asyncio
from src.retrieval.eda_retriever import EDARetriever
from src.evaluators import grade_document_relevance

async def main():
    query = "在 innovusUG 中，如何使用 mixed placer？它的流程图是怎样的？"
    metadata = {
        "categories": ["EDA"],
        "tool": "Innovus"
    }
    
    retriever = EDARetriever()
    # Fetch 50 raw chunks, rerank to top 15
    res = await retriever.aretrieve(query, metadata, fetch_k=50, top_k=15)
    
    chunks = res.get("chunks", [])
    print(f"=== Top 15 Reranked Chunks ===")
    for idx, c in enumerate(chunks, 1):
        is_relevant = await grade_document_relevance(c.page_content, query)
        print(f"[{idx}] Source: {c.metadata.get('source')} | Section: {c.metadata.get('section')} | Score: {getattr(c, 'score', 0.0)} | Relevant: {is_relevant}")
        print(f"Snippet: {c.page_content[:200]}")
        print("-" * 50)

if __name__ == '__main__':
    asyncio.run(main())
