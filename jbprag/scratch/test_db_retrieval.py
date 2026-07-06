import asyncio
import os
import sys
import json

from dotenv import load_dotenv
load_dotenv('.env')

from src.retrieval.project_retriever import aretrieve_project_docs

async def main():
    query = "1_1_flowtool_intro"
    res = await aretrieve_project_docs(query, project_id=None, metadata={"categories": ["Platform_Flow"]})
    
    chunks = res.get("chunks", [])
    print("Num chunks:", len(chunks))
    for idx, c in enumerate(chunks):
        print(f"\n================ Chunk {idx+1} ================")
        print("Page Content:")
        print(c.page_content)
        print("Metadata:", c.metadata)

if __name__ == '__main__':
    asyncio.run(main())

