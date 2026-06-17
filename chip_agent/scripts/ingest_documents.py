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

import re

def clean_text_content(text: str, watermark: Optional[str] = None) -> str:
    if not text:
        return text
    
    lines = text.splitlines()
    cleaned_lines = []
    
    # Pre-compile regexes
    patterns = [
        re.compile(r'^Page\s+\d+(?:\s+of\s+\d+)?$', re.IGNORECASE),
        re.compile(r'^Confidential(?:\s+NDA\s+Required)?$', re.IGNORECASE),
        re.compile(r'^TSMC\s+NDA\s+REQUIRED$', re.IGNORECASE),
    ]
    if watermark:
        patterns.append(re.compile(re.escape(watermark), re.IGNORECASE))
        
    for line in lines:
        stripped = line.strip()
        is_watermark = False
        for pattern in patterns:
            # If the pattern is a line-anchored regex, match whole line
            if pattern.pattern.startswith('^') and pattern.pattern.endswith('$'):
                if pattern.search(stripped):
                    is_watermark = True
                    break
            else:
                # Custom watermark pattern within the line
                if pattern.search(stripped):
                    line = pattern.sub("", line)
                    stripped = line.strip()
        
        if is_watermark or not stripped:
            continue
            
        cleaned_lines.append(line)
        
    return "\n".join(cleaned_lines)

def parse_args():
    parser = argparse.ArgumentParser(description="Ingest PDF/Excel/Markdown files into chip RAG database.")
    parser.add_argument("-f", "--file", required=True, help="Path to document file or directory of documents")
    parser.add_argument("-c", "--category", required=True, choices=["PDK", "EDA", "Project_Doc", "General"], help="Document category")
    parser.add_argument("-n", "--node", help="Process node (e.g., N5, N7)")
    parser.add_argument("-t", "--tool", help="EDA tool (e.g., Innovus, ICC2)")
    parser.add_argument("-p", "--project-id", help="Project ID (e.g., Proj_A, Proj_B)")
    parser.add_argument("-b", "--batch-size", type=int, default=100, help="Vector store indexing batch size")
    parser.add_argument("--reset", action="store_true", help="Delete existing database chunks for the document before indexing")
    parser.add_argument("--clean", action="store_true", help="Clean PDF watermarks/margins before loading")
    parser.add_argument("--header-margin", type=int, default=50, help="Header margin to redact (default 50)")
    parser.add_argument("--footer-margin", type=int, default=60, help="Footer margin to redact (default 60)")
    parser.add_argument("--watermark", help="Specific text watermark pattern to erase")
    return parser.parse_args()

def process_file(file_path: Path, args) -> Optional[List]:
    try:
        from markitdown import MarkItDown
    except ImportError:
        print("Error: 'markitdown' is not installed.", file=sys.stderr)
        print("Please install it to use this document ingestion script:", file=sys.stderr)
        print("pip install markitdown", file=sys.stderr)
        sys.exit(1)

    temp_pdf_path = None
    try:
        target_path = file_path
        if getattr(args, "clean", False) and file_path.suffix.lower() == ".pdf":
            import tempfile
            import os
            try:
                from scripts.clean_pdf import clean_pdf_file
            except ImportError:
                sys.path.append(str(Path(__file__).parent))
                from clean_pdf import clean_pdf_file
                
            temp_fd, temp_pdf_str = tempfile.mkstemp(suffix=".pdf", prefix="temp_clean_")
            os.close(temp_fd)
            temp_pdf_path = Path(temp_pdf_str)
            
            print(f"Cleaning PDF margins/watermarks to: {temp_pdf_path.name}")
            cleaned = clean_pdf_file(
                input_path=file_path,
                output_path=temp_pdf_path,
                header_margin=args.header_margin,
                footer_margin=args.footer_margin,
                watermark=args.watermark
            )
            if cleaned:
                target_path = temp_pdf_path
            else:
                print(f"Warning: PDF cleaning failed for {file_path.name}, falling back to original file.")
                temp_pdf_path = None

        md = MarkItDown()
        print(f"Converting document via MarkItDown: {target_path.name}...")
        result = md.convert(str(target_path.absolute()))
        text = result.text_content
        
        if getattr(args, "clean", False):
            text = clean_text_content(text, getattr(args, "watermark", None))
            
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
    finally:
        if temp_pdf_path and temp_pdf_path.exists():
            try:
                import os
                os.remove(temp_pdf_path)
            except Exception as e:
                print(f"Warning: Failed to delete temporary PDF {temp_pdf_path}: {e}", file=sys.stderr)

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
