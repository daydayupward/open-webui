import asyncio
from src.retrieval.project_retriever import aretrieve_project_docs
from src.retrieval.eda_retriever import aretrieve_eda_manuals
from src.retrieval.pdk_retriever import aretrieve_pdk_rules

async def test_dispatch(query: str, categories: list):
    metadata = {"categories": categories}
    project_id = None
    
    # Map categories to vector store collections
    targets = set()
    if not categories:
        targets = {"project_docs", "pdk_rules", "eda_manuals"}
    else:
        for cat in categories:
            if cat in ("PDK", "StdCell", "SRAM"):
                targets.add("pdk_rules")
            elif cat in ("EDA", "Script", "Literature"):
                targets.add("eda_manuals")
            elif cat in ("Project_Doc", "Platform_Flow", "IP"):
                targets.add("project_docs")
            else:
                targets.add("project_docs")
                
    print(f"Query: {query}")
    print(f"Categories: {categories}")
    print(f"Selected Targets: {targets}")
    
    tasks = []
    # Test with normalized metadata categories for each retriever call
    if "pdk_rules" in targets:
        pdk_meta = metadata.copy()
        # Filter to PDK categories
        pdk_meta["categories"] = [c for c in categories if c in ("PDK", "StdCell", "SRAM")]
        tasks.append(aretrieve_pdk_rules(query, pdk_meta))
        
    if "eda_manuals" in targets:
        eda_meta = metadata.copy()
        # Filter to EDA categories
        eda_meta["categories"] = [c for c in categories if c in ("EDA", "Script")]
        tasks.append(aretrieve_eda_manuals(query, eda_meta))
        
    if "project_docs" in targets:
        proj_meta = metadata.copy()
        # Filter to Project categories
        proj_meta["categories"] = [c for c in categories if c in ("Project_Doc", "Platform_Flow", "IP", "Literature")]
        tasks.append(aretrieve_project_docs(query, project_id, proj_meta))
        
    retrieval_results = await asyncio.gather(*tasks)
    
    # Merge chunks
    chunks = []
    for res in retrieval_results:
        chunks.extend(res.get("chunks", []))
        
    # Sort chunks by score descending
    chunks.sort(key=lambda x: getattr(x, "score", 0.0) or 0.0, reverse=True)
    
    print(f"Total merged chunks: {len(chunks)}")
    for i, c in enumerate(chunks[:3], 1):
        print(f"[{i}] Source: {c.metadata.get('source')} (Category: {c.metadata.get('category')}) Score: {getattr(c, 'score', None)}")
        print(c.page_content[:200])
        print()

async def main():
    # 1. Test "What is STA" with category "Literature"
    await test_dispatch("What is STA (Static Timing Analysis)?", ["Literature"])
    
if __name__ == '__main__':
    asyncio.run(main())
