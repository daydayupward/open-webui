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
import logging

logger = logging.getLogger("ingest_documents")

import base64
import mimetypes
import hashlib
import shutil

def get_image_description(image_path: Path) -> str:
    try:
        # Identify mime type
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type:
            mime_type = "image/png"
            
        with open(image_path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode("utf-8")
            
        data_url = f"data:{mime_type};base64,{encoded}"
        
        # Call visual model
        from src.utils import get_visual_llm
        from langchain_core.messages import HumanMessage
        
        visual_llm = get_visual_llm(temperature=0.0)
        message = HumanMessage(
            content=[
                {"type": "text", "text": "You are a chip physical design expert. Describe this schematic/diagram/table in detail. Identify the process node, EDA tools, metal layers, cell types, signals, DRC violations, and textual metrics shown. Output a structured description in Chinese."},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]
        )
        response = visual_llm.invoke([message])
        return response.content.strip()
    except Exception as e:
        print(f"Warning: Failed to get visual description for {image_path.name}: {e}", file=sys.stderr)
        return ""

def process_markdown_images(text: str, doc_dir: Path, category: str) -> str:
    # Check if category is in image ingestion categories
    enabled_categories = [c.strip() for c in settings.IMAGE_INGESTION_CATEGORIES.split(",")]
    if category not in enabled_categories:
        return text

    # Define target static dir
    static_dir = Path("/home/eason/proj/open-webui/backend/open_webui/static/uploads/images")
    static_dir.mkdir(parents=True, exist_ok=True)

    # Regex for markdown image links: ![alt](path "title") or ![alt](path)
    pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')

    def replacer(match):
        alt_text = match.group(1)
        link_content = match.group(2).strip()
        
        # Split path and title if present
        title = ""
        img_path_str = link_content
        if ' ' in link_content:
            parts = link_content.split(' ', 1)
            img_path_str = parts[0].strip()
            title = parts[1].strip().strip('"').strip("'")
            
        # Remove quotes around path if present
        img_path_str = img_path_str.strip('"').strip("'")
        
        # Resolve absolute path of the image relative to doc_dir
        img_path = (doc_dir / img_path_str).resolve()
        if not img_path.exists():
            print(f"Warning: Image file not found at {img_path}", file=sys.stderr)
            return match.group(0) # Keep original
            
        # Copy to static dir with deterministic name
        with open(img_path, "rb") as f:
            content = f.read()
            img_hash = hashlib.md5(content).hexdigest()
            
        suffix = img_path.suffix.lower()
        new_filename = f"{img_hash}{suffix}"
        dest_path = static_dir / new_filename
        
        # Copy file
        if not dest_path.exists():
            shutil.copy2(img_path, dest_path)
            
        web_path = f"/static/uploads/images/{new_filename}"
        
        # Get VLM description using gpt-image-2
        print(f"Generating semantic description for image: {img_path.name}...")
        description = get_image_description(img_path)
        
        # Format replacement
        title_attr = f' "{title}"' if title else ""
        replacement = f'![{alt_text}]({web_path}{title_attr})'
        if description:
            replacement += f'\n【图片语义描述：{description}】'
        return replacement

    return pattern.sub(replacer, text)

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
    parser.add_argument("-c", "--category", required=True, choices=["PDK", "StdCell", "SRAM", "IP", "EDA", "Platform_Flow", "Project_Doc", "Script", "Literature", "General"], help="Document category")
    parser.add_argument("-n", "--node", help="Process node (e.g., N5, N7)")
    parser.add_argument("-t", "--tool", help="EDA tool (e.g., Innovus, ICC2)")
    parser.add_argument("-p", "--project-id", help="Project ID (e.g., Proj_A, Proj_B)")
    parser.add_argument("-v", "--vendor", help="IP vendor (e.g., Synopsys, Cadence, TSMC)")
    parser.add_argument("-b", "--batch-size", type=int, default=100, help="Vector store indexing batch size")
    parser.add_argument("--reset", action="store_true", help="Delete existing database chunks for the document before indexing")
    parser.add_argument("--clean", action="store_true", help="Clean PDF watermarks/margins before loading")
    parser.add_argument("--header-margin", type=int, default=50, help="Header margin to redact (default 50)")
    parser.add_argument("--footer-margin", type=int, default=60, help="Footer margin to redact (default 60)")
    parser.add_argument("--watermark", help="Specific text watermark pattern to erase")
    return parser.parse_args()

def process_file(file_path: Path, args) -> Optional[List]:
    if file_path.suffix.lower() == ".pdf" and file_path.exists():
        try:
            with open(file_path, "rb") as f:
                header = f.read(50)
                if b"%TSD-Header-###%" in header:
                    print(f"Error: '{file_path.name}' is a TSMC Secure Document (TSD) encrypted with TSMC DRM.", file=sys.stderr)
                    print("Standard open-source PDF parsers cannot read DRM-protected TSD files directly.", file=sys.stderr)
                    print("Please decrypt the file first (e.g., by printing to a standard PDF or exporting to plain text) and ingest the decrypted file.", file=sys.stderr)
                    return None
        except Exception as e:
            logger.warning("Failed to check file header for %s: %s", file_path.name, e)

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

        suffix = file_path.suffix.lower()
        if suffix in (".md", ".txt"):
            print(f"Reading text/markdown document directly: {file_path.name}...")
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            if suffix == ".md":
                text = process_markdown_images(text, file_path.parent, args.category)
        elif suffix == ".pdf":
            try:
                import pymupdf4llm
                import tempfile
                import shutil
                
                temp_img_dir = Path(tempfile.mkdtemp(prefix="pdf_images_"))
                try:
                    print(f"Converting PDF document via PyMuPDF4LLM: {target_path.name}...")
                    text = pymupdf4llm.to_markdown(
                        str(target_path.absolute()),
                        write_images=True,
                        image_path=str(temp_img_dir.absolute()),
                        image_format="png"
                    )
                    # Process extracted images with VLM & copy them to static directory
                    text = process_markdown_images(text, temp_img_dir, args.category)
                finally:
                    if temp_img_dir.exists():
                        shutil.rmtree(temp_img_dir)
            except ImportError:
                print("Warning: 'pymupdf4llm' is not installed. Falling back to MarkItDown for PDF.")
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(str(target_path.absolute()))
                text = result.text_content
        elif suffix in (".docx", ".xlsx", ".xls", ".pptx", ".html"):
            try:
                from markitdown import MarkItDown
            except ImportError:
                print("Error: 'markitdown' is not installed.", file=sys.stderr)
                print("Please install it to use this document ingestion script:", file=sys.stderr)
                print("pip install markitdown", file=sys.stderr)
                sys.exit(1)
            md = MarkItDown()
            print(f"Converting Office/HTML document via MarkItDown: {target_path.name}...")
            result = md.convert(str(target_path.absolute()))
            text = result.text_content
        else:
            print(f"Warning: Unsupported file format {suffix} for {file_path.name}. Trying MarkItDown fallback.")
            try:
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(str(target_path.absolute()))
                text = result.text_content
            except ImportError:
                print(f"Error: Unsupported format and markitdown not available for {file_path.name}")
                return None
        
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
                "project_id": args.project_id,
                "vendor": getattr(args, "vendor", None)
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
        "StdCell": "pdk_rules",
        "SRAM": "pdk_rules",
        "EDA": "eda_manuals",
        "IP": "project_docs",
        "Platform_Flow": "project_docs",
        "Project_Doc": "project_docs",
        "Script": "project_docs",
        "Literature": "project_docs",
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
