import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append('/home/eason/proj/open-webui/chip_agent')
load_dotenv('/home/eason/proj/open-webui/chip_agent/.env')

from src.utils import get_llm
from src.prompts.supervisor_prompt import SYSTEM_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage

async def test_supervisor(query):
    llm = get_llm()
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    messages = [system_message, HumanMessage(content=query)]
    
    print(f"--- Query: {query} ---")
    try:
        response = await llm.ainvoke(messages)
        print("Raw Content:")
        print(response.content)
    except Exception as e:
        print("Failed:", e)

async def main():
    await test_supervisor("what is sta")
    await test_supervisor("What is STA (Static Timing Analysis)?")

if __name__ == '__main__':
    asyncio.run(main())
