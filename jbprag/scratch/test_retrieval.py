import asyncio
from src.retrieval.project_retriever import retrieve_project_docs
from src.retrieval.pdk_retriever import retrieve_pdk_rules
from src.retrieval.eda_retriever import retrieve_eda_manuals
from src.supervisor import arun_supervisor
from langchain_core.messages import HumanMessage

async def main():
    query = 'What is STA (Static Timing Analysis)?'
    
    # 1. Test supervisor routing
    print("=== Test Supervisor Routing ===")
    state_messages = [HumanMessage(content=query)]
    res = await arun_supervisor(state_messages)
    print(f"Route: {res.get('route')}")
    print(f"Metadata: {res.get('metadata')}")
    print()
    
    # 2. Test PDK Retriever
    print("=== Test PDK Retriever ===")
    try:
        pdk_res = retrieve_pdk_rules(query, metadata={})
        print(f"PDK Chunks retrieved: {len(pdk_res.get('chunks', []))}")
        print(f"PDK Logs: {pdk_res.get('logs')}")
    except Exception as e:
        print(f"PDK Retriever error: {e}")
    print()
    
    # 3. Test EDA Retriever
    print("=== Test EDA Retriever ===")
    try:
        eda_res = retrieve_eda_manuals(query, metadata={})
        print(f"EDA Chunks retrieved: {len(eda_res.get('chunks', []))}")
        print(f"EDA Logs: {eda_res.get('logs')}")
    except Exception as e:
        print(f"EDA Retriever error: {e}")
    print()
    
    # 4. Test Project Retriever
    print("=== Test Project Retriever ===")
    try:
        proj_res = retrieve_project_docs(query, metadata={})
        print(f"Project Chunks retrieved: {len(proj_res.get('chunks', []))}")
        print(f"Project Logs: {proj_res.get('logs')}")
    except Exception as e:
        print(f"Project Retriever error: {e}")
    print()

if __name__ == '__main__':
    asyncio.run(main())
