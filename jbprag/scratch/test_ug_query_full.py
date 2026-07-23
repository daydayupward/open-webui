import asyncio
import logging
from src.graph import build_graph
from langchain_core.messages import HumanMessage

logging.basicConfig(level=logging.INFO)

async def main():
    query = "Show me the clock mesh structure and diagram from innovusUG.pdf"
    print(f"=== Running Query: '{query}' ===")
    
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "temperature": 0.0
    }
    
    agent = build_graph()
    res = await agent.ainvoke(initial_state)
    
    print("\n=== Route & Metadata ===")
    print(f"Route: {res.get('route')}")
    print(f"Metadata: {res.get('metadata')}")
    
    print("\n=== Final Answer ===")
    print(res.get("final_answer"))
    
    print("\n=== Retrieved Docs ===")
    for idx, doc in enumerate(res.get("retrieved_docs", []), 1):
        print(f"[{idx}] Source: {doc.get('metadata', {}).get('source')} Category: {doc.get('metadata', {}).get('category')}")
        print(f"Content snippet: {doc.get('content')[:300]}")
        print("-" * 50)

if __name__ == '__main__':
    asyncio.run(main())
