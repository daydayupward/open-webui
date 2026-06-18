import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append('/home/eason/proj/open-webui/chip_agent')
load_dotenv('/home/eason/proj/open-webui/chip_agent/.env')

from src.graph import build_graph
from langchain_core.messages import HumanMessage

async def run_query(query):
    agent = build_graph()
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "request_id": "test_req",
        "temperature": 0.0,
        "route": "",
        "metadata": {},
        "retrieved_docs": [],
        "tool_logs": [],
        "final_answer": "",
        "errors": []
    }
    
    print(f"\n================ QUERY: {query} ================")
    result = await agent.ainvoke(initial_state)
    print("--- Route:", result.get("route"))
    print("--- Retrieved Docs Count:", len(result.get("retrieved_docs", [])))
    for i, doc in enumerate(result.get("retrieved_docs", [])):
        print(f"  Doc {i}: content: {doc['content'][:150]}...")
        print(f"  Doc {i} meta: {doc['metadata']}")
    print("--- Final Answer:")
    print(result.get("final_answer"))

async def main():
    await run_query("What is STA?")
    await run_query("What is static timing analysis?")

if __name__ == '__main__':
    asyncio.run(main())
