import asyncio
from pathlib import Path
from src.ingestion.loader import IngestionDocument
from src.ingestion.chunker import chunk_document
from src.ingestion.metadata_mapper import map_chunks
from src.ingestion.indexer import index_chunks
from src.retrieval.eda_retriever import EDARetriever
from src.utils import get_embeddings
from src.settings import settings

async def main():
    print("=== Verification of Parent-Child Chunking ===")
    
    # 1. Load document
    file_path = Path("scratch/test_doc.md")
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    doc = IngestionDocument(
        text=text,
        metadata={"category": "EDA", "tool": "Innovus"},
        source=str(file_path.absolute())
    )
    
    # 2. Chunk document (max parent tokens = 2000)
    print("\n--- Step 2: Chunking Document ---")
    chunks = chunk_document(doc, max_chunk_tokens=2000, overlap_tokens=500)
    print(f"Total chunks produced: {len(chunks)}")
    
    for idx, c in enumerate(chunks):
        print(f"\nChunk [{idx + 1}]:")
        print(f"  Child Text (first 100 chars): {repr(c.text[:100])}")
        print(f"  Child Text Token Length: {len(c.text.split())} words")
        parent_text = c.metadata.parent_metadata.get("parent_text")
        print(f"  Parent Text (first 100 chars): {repr(parent_text[:100]) if parent_text else 'MISSING!'}")
        print(f"  Parent Text Total Length: {len(parent_text.split()) if parent_text else 0} words")
        print(f"  Section: {c.metadata.section}")
        
    # 3. Map metadata and index in vector store
    print("\n--- Step 3: Mapping and Indexing ---")
    embeddings = get_embeddings()
    index_res = index_chunks(
        chunks,
        connection_string=settings.DATABASE_URL,
        collection_name="eda_manuals",
        embeddings=embeddings
    )
    print(f"Indexing completed: {index_res}")
    
    # 4. Retrieve via retriever and verify parent text swap
    print("\n--- Step 4: Retrieving from Database ---")
    retriever = EDARetriever()
    # Query for the flowchart
    query = "Where is the placement flowchart?"
    metadata = {"category": "EDA"}
    
    retrieval_res = await retriever.aretrieve(query, metadata, top_k=2)
    retrieved_chunks = retrieval_res.get("chunks", [])
    print(f"Retrieved {len(retrieved_chunks)} chunks for query: '{query}'")
    
    for idx, c in enumerate(retrieved_chunks):
        print(f"\nRetrieved Chunk [{idx + 1}] (Score: {getattr(c, 'score', 0.0)}):")
        print(f"  Content Passed to LLM (first 300 chars):\n{c.page_content[:300]}")
        print(f"  Source: {c.metadata.get('source')}")
        print(f"  Has Image: {'/static/uploads/images/' in c.page_content}")

if __name__ == '__main__':
    asyncio.run(main())
