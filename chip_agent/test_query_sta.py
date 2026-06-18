import asyncio
from src.graph import build_graph
from langchain_core.messages import HumanMessage
from src.state import AgentState

async def main():
    agent = build_graph()
    state = {'messages': [HumanMessage(content='What is STA (Static Timing Analysis)?')]}
    
    print('Invoking agent...')
    result = await agent.ainvoke(state)
    print('\nFinal output:')
    print(result['messages'][-1].content)
    
if __name__ == '__main__':
    asyncio.run(main())
