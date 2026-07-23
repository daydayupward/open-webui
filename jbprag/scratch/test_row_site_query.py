import asyncio
from src.retrieval.eda_retriever import aretrieve_eda_manuals

async def main():
    query = "参考innovusUG手册中的图示，解释在物理设计中，Block 的 Row 结构与 Site 之间的对齐关系，以及它是如何影响 Standard Cell 放置的"
    metadata = {"category": "EDA", "tool": "Innovus"}
    
    print(f"=== Testing Query: {query} ===")
    
    # 1. Test Retrieval
    res = await aretrieve_eda_manuals(query, metadata, top_k=10)
    chunks = res.get("chunks", [])
    print(f"Retrieved {len(chunks)} chunks:")
    
    image_chunks = []
    for idx, c in enumerate(chunks):
        has_image = "/static/uploads/images/" in c.page_content
        if has_image:
            image_chunks.append(c)
        print(f"[{idx+1}] Score: {getattr(c, 'score', 0.0):.2f} | Has Image: {has_image} | Section: {c.metadata.get('section')}")
        print(f"     Content snippet: {repr(c.page_content[:150])}\n")
        
    print(f"Total chunks with image markdown: {len(image_chunks)}")
    if image_chunks:
        for idx, img_c in enumerate(image_chunks):
            print(f"\n--- Image Chunk [{idx+1}] Full Image Tag ---")
            import re
            img_tags = re.findall(r'!\[.*?\]\(.*?\)', img_c.page_content)
            print("Found image tags:", img_tags)

if __name__ == '__main__':
    asyncio.run(main())
