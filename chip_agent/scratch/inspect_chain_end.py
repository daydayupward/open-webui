import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append('/home/eason/proj/open-webui/chip_agent')
load_dotenv('/home/eason/proj/open-webui/chip_agent/.env')

from src.graph import build_graph
from langchain_core.messages import HumanMessage

async def main():
    graph = build_graph()
    initial_state = {
        "messages": [HumanMessage(content="What is STA?")],
        "request_id": "test_req",
        "temperature": 0.0,
        "route": "",
        "metadata": {},
        "retrieved_docs": [],
        "tool_logs": [],
        "final_answer": "",
        "errors": []
    }
    
    async for event in graph.astream_events(initial_state, version="v2"):
        event_type = event.get("event")
        name = event.get("name")
        if event_type == "on_chain_end":
            data = event.get("data", {})
            output = data.get("output")
            print(f"Event: {event_type} | Name: {name} | Output keys: {list(output.keys()) if isinstance(output, dict) else type(output)}")
            if isinstance(output, dict) and "final_answer" in output:
                print("  Found final_answer:", repr(output["final_answer"][:100]))

if __name__ == '__main__':
    asyncio.run(main())
