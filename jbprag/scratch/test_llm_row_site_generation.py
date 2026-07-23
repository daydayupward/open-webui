import asyncio
from src.retrieval.eda_retriever import aretrieve_eda_manuals
from src.utils import get_llm
from src.prompts.eda_prompt import EDA_SCRIPT_GENERATION_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage

async def main():
    query = "参考innovusUG手册中的图示，解释在物理设计中，Block 的 Row 结构与 Site 之间的对齐关系，以及它是如何影响 Standard Cell 放置的"
    metadata = {"category": "EDA", "tool": "Innovus"}
    
    retrieval_res = await aretrieve_eda_manuals(query, metadata, top_k=10)
    chunks = retrieval_res.get("chunks", [])
    
    context_list = []
    for idx, c in enumerate(chunks):
        source_name = c.metadata.get("name") or c.metadata.get("source") or "Document"
        context_list.append(f"[{idx + 1}] Source: {source_name}\nContent: {c.page_content}")
    context_str = "\n\n".join(context_list)
    
    system_prompt = SystemMessage(
        content=EDA_SCRIPT_GENERATION_PROMPT.format(context=context_str)
    )
    user_msg = HumanMessage(content=query)
    
    llm = get_llm(0.0)
    print("=== Sending request to LLM ===")
    response = await llm.ainvoke([system_prompt, user_msg])
    
    print("\n=== LLM Response ===")
    print(response.content)
    
    print("\n--- Image tags check in LLM output ---")
    import re
    imgs = re.findall(r'!\[.*?\]\(.*?\)', response.content)
    print("Found image tags in LLM output:", imgs)

if __name__ == '__main__':
    asyncio.run(main())
