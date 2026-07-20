import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append('/home/eason/proj/open-webui/jbprag')
load_dotenv('/home/eason/proj/open-webui/jbprag/.env')

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
    
    print("Streaming events...")
    async for event in graph.astream_events(initial_state, version="v2"):
        event_type = event.get("event")
        name = event.get("name")
        metadata = event.get("metadata", {})
        node = metadata.get("langgraph_node", "")
        
        if event_type == "on_chat_model_stream":
            print(f"Event: {event_type} | Name: {name} | Node: {node}")
            data = event.get("data", {})
            chunk = data.get("chunk")
            if chunk and hasattr(chunk, "content"):
                print(f"  Content chunk: {repr(chunk.content)}")

if __name__ == '__main__':
    asyncio.run(main())
