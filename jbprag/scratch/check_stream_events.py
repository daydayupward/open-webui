import asyncio
from src.graph import build_graph
from langchain_core.messages import HumanMessage

async def main():
    query = "Show me the clock mesh structure and diagram from innovusUG.pdf"
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "temperature": 0.0
    }
    
    agent = build_graph()
    async for event in agent.astream_events(initial_state, version="v2"):
        event_type = event.get("event")
        name = event.get("name")
        parent_ids = event.get("parent_ids", [])
        if event_type == "on_chain_end":
            print(f"on_chain_end | Name: {name} | Parent IDs: {parent_ids}")

if __name__ == '__main__':
    asyncio.run(main())
