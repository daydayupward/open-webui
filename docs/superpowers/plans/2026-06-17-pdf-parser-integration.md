# PDF/PDK Ingestion CLI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a robust, decoupled CLI tool using `markitdown` to ingest real-world PDF/PDK/Excel documents, chunk them via the structure-aware chunker, and index them into the PostgreSQL vector store.

**Architecture:** Create `jbprag/scripts/ingest_documents.py` as an entry point. Check for `markitdown` dynamically. Call `chunk_document()` and `index_chunks()` to run the ingestion pipeline.

**Tech Stack:** Python 3.12, argparse, MarkItDown, LangChain, PostgreSQL, pytest

---

### File Structure Changes

- **Create**: `jbprag/scripts/ingest_documents.py` (CLI entry point for doc ingestion)
- **Create**: `jbprag/tests/test_ingestion_cli.py` (Unit and integration tests for the CLI tool)

---

### Task 1: Create the Ingestion CLI script

**Files:**
- Create: `jbprag/scripts/ingest_documents.py`

- [ ] **Step 1: Write the CLI code in `jbprag/scripts/ingest_documents.py`**
  Write a script that parses CLI arguments and integrates with the existing chunker and indexer.

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Core imports (ensure markitdown is loaded dynamically)
from src.settings import settings
from src.utils import get_embeddings
from src.ingestion.loader import IngestionDocument
from src.ingestion.chunker import chunk_document
from src.ingestion.indexer import index_chunks, delete_by_doc_id
from src.ingestion.metadata_mapper import _generate_doc_id

def parse_args():
    parser = argparse.ArgumentParser(description="Ingest PDF/Excel/Markdown files into chip RAG database.")
    parser.add_argument("-f", "--file", required=True, help="Path to document file or directory of documents")
    parser.add_argument("-c", "--category", required=True, choices=["PDK", "EDA", "Project_Doc", "General"], help="Document category")
    parser.add_argument("-n", "--node", help="Process node (e.g., N5, N7)")
    parser.add_argument("-t", "--tool", help="EDA tool (e.g., Innovus, ICC2)")
    parser.add_argument("-p", "--project-id", help="Project ID (e.g., Proj_A, Proj_B)")
    parser.add_argument("-b", "--batch-size", type=int, default=100, help="Vector store indexing batch size")
    parser.add_argument("--reset", action="store_true", help="Delete existing database chunks for the document before indexing")
    return parser.parse_args()

def process_file(file_path: Path, args) -> Optional[List]:
    try:
        from markitdown import MarkItDown
    except ImportError:
        print("Error: 'markitdown' is not installed.", file=sys.stderr)
        print("Please install it to use this document ingestion script:", file=sys.stderr)
        print("pip install markitdown", file=sys.stderr)
        sys.exit(1)

    try:
        md = MarkItDown()
        print(f"Converting document via MarkItDown: {file_path.name}...")
        result = md.convert(str(file_path.absolute()))
        text = result.text_content
        if not text or not text.strip():
            print(f"Warning: No text extracted from {file_path.name}")
            return None
            
        doc = IngestionDocument(
            text=text,
            metadata={
                "category": args.category,
                "node": args.node,
                "tool": args.tool,
                "project_id": args.project_id
            },
            source=str(file_path.absolute())
        )
        return chunk_document(doc)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        return None

def main():
    args = parse_args()
    input_path = Path(args.file)
    
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)
        
    files_to_process = []
    if input_path.is_file():
        files_to_process.append(input_path)
    else:
        # Scan directory for standard document formats
        supported_exts = {".pdf", ".md", ".docx", ".xlsx", ".txt"}
        for f in input_path.rglob("*"):
            if f.is_file() and f.suffix.lower() in supported_exts:
                files_to_process.append(f)
                
    if not files_to_process:
        print("No supported files found to process.")
        return

    print(f"Found {len(files_to_process)} file(s) to process.")
    
    embeddings = get_embeddings()
    connection_string = settings.DATABASE_URL
    collection_mapping = {
        "PDK": "pdk_rules",
        "EDA": "eda_manuals",
        "Project_Doc": "project_docs",
        "General": "project_docs"
    }
    collection_name = collection_mapping[args.category]
    
    for file_path in files_to_process:
        chunks = process_file(file_path, args)
        if not chunks:
            continue
            
        if args.reset:
            # Generate doc_id based on source and first 200 chars of raw content (just like metadata mapper does)
            raw_text = chunks[0].metadata.parent_metadata.get("text_prefix", "") if hasattr(chunks[0], "metadata") else ""
            doc_id = _generate_doc_id(str(file_path.absolute()), chunks[0].text)
            print(f"Resetting existing database records for doc_id={doc_id}...")
            delete_by_doc_id(doc_id, connection_string, collection_name, embeddings)
            
        print(f"Indexing {len(chunks)} chunks into vector store collection '{collection_name}'...")
        stats = index_chunks(
            chunks=chunks,
            connection_string=connection_string,
            collection_name=collection_name,
            embeddings=embeddings,
            batch_size=args.batch_size
        )
        print(f"File {file_path.name} indexed successfully. Stats: {stats}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add execute permission to the script**
  Run: `chmod +x jbprag/scripts/ingest_documents.py`

- [ ] **Step 3: Commit script code**
  Run: `git add jbprag/scripts/ingest_documents.py`
  Run: `git commit -m "feat: add ingest_documents.py CLI ingestion tool"`

---

### Task 2: Create unit tests for the ingestion script

**Files:**
- Create: `jbprag/tests/test_ingestion_cli.py`

- [ ] **Step 1: Write test code in `jbprag/tests/test_ingestion_cli.py`**
  Add mock-based unit tests for argument parsing and flow invocation.

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from scripts.ingest_documents import parse_args, process_file

@patch("sys.argv", ["ingest_documents.py", "-f", "dummy.pdf", "-c", "PDK", "-n", "N5", "-t", "Innovus"])
def test_parse_args():
    args = parse_args()
    assert args.file == "dummy.pdf"
    assert args.category == "PDK"
    assert args.node == "N5"
    assert args.tool == "Innovus"
    assert args.reset is False

@patch("scripts.ingest_documents.MarkItDown")
@patch("scripts.ingest_documents.chunk_document")
def test_process_file_success(mock_chunk_document, mock_markitdown):
    # Setup MarkItDown mock
    mock_md_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.text_content = "This is sample PDK text about N5 metal pitch."
    mock_md_instance.convert.return_value = mock_result
    mock_markitdown.return_value = mock_md_instance

    # Setup chunker mock
    mock_chunk_document.return_value = ["chunk1", "chunk2"]

    class ArgsMock:
        category = "PDK"
        node = "N5"
        tool = "Innovus"
        project_id = None

    chunks = process_file(Path("test.pdf"), ArgsMock())
    assert chunks == ["chunk1", "chunk2"]
    mock_md_instance.convert.assert_called_once_with(str(Path("test.pdf").absolute()))
```

- [ ] **Step 2: Run the new unit test**
  Run: `PYTHONPATH=jbprag python3 -m pytest jbprag/tests/test_ingestion_cli.py -v`
  Expected: PASS

- [ ] **Step 3: Commit the test code**
  Run: `git add jbprag/tests/test_ingestion_cli.py`
  Run: `git commit -m "test: add unit tests for ingest_documents CLI"`

---

### Task 3: Full Ingest Verification

- [ ] **Step 1: Run full pytest suite**
  Run: `PYTHONPATH=jbprag python3 -m pytest -v`
  Expected: All tests pass

- [ ] **Step 2: Dry-run test of the script without markitdown (or with install)**
  Verify dependencies output instructions correctly when run on a dummy file.
