import asyncio
from src.retrieval.eda_retriever import EDARetriever

async def main():
    query = "InnovusUG mixed placer flow chart flow steps"
    print(f"=== Running Raw Retrieval for: '{query}' ===")
    
    retriever = EDARetriever()
    # Run retrieve with empty metadata so no hard filter is applied
    res = await retriever.aretrieve(query, {}, fetch_k=20, top_k=10)
    
    chunks = res.get("chunks", [])
    print(f"Retrieved {len(chunks)} chunks:")
    for idx, c in enumerate(chunks, 1):
        print(f"[{idx}] Source: {c.metadata.get('source')} | Section: {c.metadata.get('section')} | Score: {c.metadata.get('score', 0.0)}")
        print(f"Snippet: {c.page_content[:200]}")
        print("-" * 50)

if __name__ == '__main__':
    asyncio.run(main())
