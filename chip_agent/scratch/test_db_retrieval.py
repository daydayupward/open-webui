import asyncio
import os
import sys
import json

from dotenv import load_dotenv
load_dotenv('.env')

from src.retrieval.project_retriever import aretrieve_project_docs

async def main():
    query = "Explain the timing derating guidelines for late paths according to the nanometer designs book."
    res = await aretrieve_project_docs(query, project_id=None)
    
    print("Num chunks:", len(res.get("chunks", [])))
    for idx, c in enumerate(res.get("chunks", [])):
        print(f"Chunk {idx+1}:")
        print("Page Content type:", type(c.page_content))
        print("Page Content len:", len(c.page_content))
        print("Page Content sample:", repr(c.page_content[:100]))
        print("Metadata:", c.metadata)
        print("Model dump:", c.model_dump())

if __name__ == '__main__':
    asyncio.run(main())
