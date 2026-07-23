import asyncio
from src.retrieval.eda_retriever import retrieve_eda_manuals

def main():
    query = 'What is STA (Static Timing Analysis)?'
    print("=== Retrieve from EDA manuals ===")
    res = retrieve_eda_manuals(query, metadata={})
    chunks = res.get("chunks", [])
    print(f"Chunks retrieved: {len(chunks)}")
    for i, c in enumerate(chunks, 1):
        print(f"[{i}] Source: {c.metadata.get('source')} Page: {c.metadata.get('page')}")
        print(f"Score/Metadata: {c.metadata}")
        print(c.page_content[:400])
        print("-" * 50)

if __name__ == '__main__':
    main()
