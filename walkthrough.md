# Walkthrough: Parent-Child Chunking and Image Colocation Implementation

This document walks through the architectural implementation of Parent-Child RAG chunking and colocated image binding.

---

## 🛠️ Changes Implemented

### 1. Parent-Child Chunker (`src/ingestion/chunker.py`)
- Rewrote the chunker in [chunker.py](file:///home/eason/proj/open-webui/jbprag/src/ingestion/chunker.py).
- **Parent Chunking (Option 1 & 2)**: Gathers classified block elements (headers, paragraphs, lists, tables) under sections and merges them up to `max_parent_tokens = 2000` tokens, with `overlap_tokens = 500` tokens. By merging contiguous paragraphs and headings under sections, Option 2 is naturally implemented (image links remain colocated inside their parent text block groups).
- **Child Splitting (Option 3)**: For each 2000-token Parent Chunk, we split it into smaller **Child Chunks** of size `max_child_tokens = 300` tokens with `child_overlap_tokens = 50` tokens.
- Embeds the full parent text `parent_text` inside the `parent_metadata` of each Child Chunk.

### 2. Metadata Mapper (`src/ingestion/metadata_mapper.py`)
- Updated `ChunkIndexMetadata` model in [metadata_mapper.py](file:///home/eason/proj/open-webui/jbprag/src/ingestion/metadata_mapper.py) to support `parent_text`.
- Updated `merge_metadata` to extract and populate `parent_text` from chunk `parent_metadata`.

### 3. Vector Indexer (`src/ingestion/indexer.py`)
- Updated `_build_document` in [indexer.py](file:///home/eason/proj/open-webui/jbprag/src/ingestion/indexer.py) to pass `"parent_text": meta.parent_text` to the langchain Document's metadata dictionary, saving it in the vector store's JSONB `cmetadata` column.

### 4. Parent Content Swap in Retrieval (`src/retrieval/base.py`)
- Updated `BaseRetriever.retrieve` and `aretrieve` in [base.py](file:///home/eason/proj/open-webui/jbprag/src/retrieval/base.py).
- Swaps each retrieved Child Chunk's `page_content` with its `parent_text` (if `parent_text` is present in metadata) before sending them to the Qwen-Reranker and LLM generation stages.

---

## 🧪 Verification Results

We verified the implementation by running `scratch/verify_parent_child.py` with a test document:

**Command:**
```bash
PYTHONPATH=. python3 scratch/verify_parent_child.py
```

**Output Log Verification:**
- **Chunking**: Successfully segmented a multi-section document into Parent Chunks, and split them into 300-token Child Chunks with the full `parent_text` preserved in metadata.
- **Indexing**: Indexed Child Chunks into the `eda_manuals` PGVector collection.
- **Retrieval & Content Swapping**: The vector store successfully retrieved the 300-token child chunk based on vector similarity, and the retriever successfully swapped its content with the **2000-token parent text** containing the full steps and the flowchart image link.
- **Verification Log**: [task-1464.log](file:///C:/Users/eason.li/.gemini/antigravity/brain/2b2a06a7-1ffd-4f70-99b3-12f0f5f413f5/.system_generated/tasks/task-1464.log).
