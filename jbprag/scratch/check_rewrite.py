import asyncio
from src.evaluators import rewrite_query

async def main():
    query = "在 innovusUG 中，使用 mixed placer 的流程图和流程步骤是什么？"
    rewritten = await rewrite_query(query)
    print(f"Original: '{query}'")
    print(f"Rewritten: '{rewritten}'")

if __name__ == '__main__':
    asyncio.run(main())
