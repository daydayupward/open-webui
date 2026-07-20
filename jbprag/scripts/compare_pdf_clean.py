#!/usr/bin/env python3
import argparse
import sys
import difflib
from pathlib import Path

def extract_pdf_page_text(pdf_path: Path, max_pages: int = 3) -> list[str]:
    try:
        import fitz
    except ImportError:
        print("Error: 'pymupdf' is not installed.", file=sys.stderr)
        sys.exit(1)
        
    doc = fitz.open(pdf_path)
    pages_text = []
    for idx, page in enumerate(doc):
        if idx >= max_pages:
            break
        pages_text.append(page.get_text())
    doc.close()
    return pages_text

def main():
    parser = argparse.ArgumentParser(description="Compare text extraction between original and cleaned PDFs.")
    parser.add_argument("-orig", "--original", required=True, help="Original PDF file path")
    parser.add_argument("-clean", "--cleaned", required=True, help="Cleaned PDF file path")
    parser.add_argument("-p", "--pages", type=int, default=3, help="Number of pages to compare (default 3)")
    args = parser.parse_args()

    orig_path = Path(args.original)
    clean_path = Path(args.cleaned)

    if not orig_path.exists() or not clean_path.exists():
        print("Error: One of the PDF files does not exist.", file=sys.stderr)
        sys.exit(1)

    orig_texts = extract_pdf_page_text(orig_path, args.pages)
    clean_texts = extract_pdf_page_text(clean_path, args.pages)

    print(f"=== Comparing First {args.pages} Pages of Text Extraction ===")
    
    for i in range(min(len(orig_texts), len(clean_texts))):
        print(f"\n--- Page {i+1} Diff ---")
        orig_lines = orig_texts[i].splitlines()
        clean_lines = clean_texts[i].splitlines()
        
        diff = difflib.unified_diff(
            orig_lines,
            clean_lines,
            fromfile=orig_path.name,
            tofile=clean_path.name,
            lineterm=""
        )
        
        has_diff = False
        for line in diff:
            has_diff = True
            # Print additions/removals with colors if terminal supports it
            if line.startswith("-") and not line.startswith("---"):
                print(f"\033[91m{line}\033[0m") # Red
            elif line.startswith("+") and not line.startswith("+++"):
                print(f"\033[92m{line}\033[0m") # Green
            else:
                print(line)
        if not has_diff:
            print("No differences found on this page.")

if __name__ == "__main__":
    main()
