import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append('/home/eason/proj/open-webui/chip_agent')
load_dotenv('/home/eason/proj/open-webui/chip_agent/.env')

from src.retrieval.project_retriever import aretrieve_project_docs

async def test_retrieval(query):
    print(f"--- Query: {query} ---")
    res = await aretrieve_project_docs(query, project_id=None)
    print("Logs:")
    print(res["logs"])
    print("Chunks count:", len(res["chunks"]))
    for i, c in enumerate(res["chunks"]):
        print(f"  Chunk {i}: {c.page_content[:150]}...")
        print(f"  Metadata: {c.metadata}")

async def main():
    await test_retrieval("what is sta")
    await test_retrieval("What is STA (Static Timing Analysis)?")

if __name__ == '__main__':
    asyncio.run(main())
