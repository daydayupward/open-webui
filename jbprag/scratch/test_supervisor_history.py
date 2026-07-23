import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from src.supervisor import arun_supervisor

# Simulated 2-turn conversation history
messages = [
    HumanMessage(content="在 innovusUG 中使用 mixed placer 的流程是什么？"),
    AIMessage(content="""根据检索到的文档，以下是 Innovus 中进行 Mixed Placer 的详细流程：
1. 导入设计
2. 设置布局模式使用 setPlaceMode
3. 运行 mixed placement
4. 验证布局。图片显示如下：
![](/static/uploads/images/d2db46ea46ac64cb7ad2d0e6e3d42309.png)"""),
    HumanMessage(content="在 Innovus 中进行 CTS 的详细流程是什么？结合图片说明。")
]

async def main():
    print("=== Running Supervisor with Multi-Turn History ===")
    res = await arun_supervisor(messages)
    print("Result:")
    import pprint
    pprint.pprint(res)

if __name__ == '__main__':
    asyncio.run(main())
