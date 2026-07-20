# PDF Watermark and Margins Cleaner Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a PDF cleaning pipeline (removing stamps, redacting header/footer margins, and applying regex text post-filtering) along with a standalone comparison tool to let engineers audit the cleaning effect.

**Architecture:** Create `scripts/clean_pdf.py` for physical PDF cleaning. Create `scripts/compare_pdf_clean.py` to print comparative text differences. Modify `scripts/ingest_documents.py` to support `--clean` dynamically using temporary cleaned PDFs.

**Tech Stack:** Python 3.12, PyMuPDF (fitz), argparse, difflib, pytest

---

### File Structure Changes

- **Create**: `jbprag/scripts/clean_pdf.py` (PDF physical watermark & margin eraser)
- **Create**: `jbprag/scripts/compare_pdf_clean.py` (CLI visual comparative diff tool)
- **Modify**: `jbprag/scripts/ingest_documents.py` (Integrate optional cleaning stage)
- **Create**: `jbprag/tests/test_pdf_cleaner.py` (Unit tests for the cleaner and regex logic)

---

### Task 1: Create the PDF physical cleaning script

**Files:**
- Create: `jbprag/scripts/clean_pdf.py`

- [ ] **Step 1: Write the code in `jbprag/scripts/clean_pdf.py`**
  Implement the PDF redaction using PyMuPDF.

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

def clean_pdf_file(
    input_path: Path,
    output_path: Path,
    header_margin: int = 50,
    footer_margin: int = 60,
    watermark: str = None
) -> bool:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Error: 'pymupdf' is not installed.", file=sys.stderr)
        print("Please install it: pip install pymupdf", file=sys.stderr)
        return False

    try:
        doc = fitz.open(input_path)
        for page in doc:
            # 1. Delete stamp annotations (Electronic Watermarks)
            for annot in page.annots():
                if annot.type[0] == 8:  # 8 is Stamp annotation
                    page.delete_annot(annot)

            # 2. Redact header and footer margins
            w, h = page.rect.width, page.rect.height
            if header_margin > 0:
                header_rect = fitz.Rect(0, 0, w, header_margin)
                page.add_redact_annot(header_rect, fill=(1, 1, 1))
            if footer_margin > 0:
                footer_rect = fitz.Rect(0, h - footer_margin, w, h)
                page.add_redact_annot(footer_rect, fill=(1, 1, 1))

            # 3. Redact specific text watermarks if pattern is provided
            if watermark:
                text_instances = page.search_for(watermark)
                for rect in text_instances:
                    page.add_redact_annot(rect, fill=(1, 1, 1))

            # Apply redactions to physically erase content
            page.apply_redactions()

        # Save to output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return True
    except Exception as e:
        print(f"Error cleaning PDF {input_path.name}: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Clean watermarks and margins from a PDF file physically.")
    parser.add_argument("-i", "--input", required=True, help="Input PDF file path")
    parser.add_argument("-o", "--output", help="Output cleaned PDF path")
    parser.add_argument("--header-margin", type=int, default=50, help="Margin height to crop at top (default 50)")
    parser.add_argument("--footer-margin", type=int, default=60, help="Margin height to crop at bottom (default 60)")
    parser.add_argument("--watermark", help="Specific text watermark pattern to erase")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
    
    success = clean_pdf_file(
        input_path=input_path,
        output_path=output_path,
        header_margin=args.header_margin,
        footer_margin=args.footer_margin,
        watermark=args.watermark
    )
    if success:
        print(f"Successfully cleaned PDF. Saved to: {output_path}")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add execute permission to the cleaner script**
  Run: `chmod +x jbprag/scripts/clean_pdf.py`

- [ ] **Step 3: Commit the cleaner script**
  Run: `git add jbprag/scripts/clean_pdf.py`
  Run: `git commit -m "feat: add clean_pdf.py physical PDF cleaner"`

---

### Task 2: Create the PDF comparison script

**Files:**
- Create: `jbprag/scripts/compare_pdf_clean.py`

- [ ] **Step 1: Write the comparison logic in `jbprag/scripts/compare_pdf_clean.py`**
  Implement text diff printing.

```python
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
```

- [ ] **Step 2: Add execute permission and commit**
  Run: `chmod +x jbprag/scripts/compare_pdf_clean.py`
  Run: `git add jbprag/scripts/compare_pdf_clean.py`
  Run: `git commit -m "feat: add compare_pdf_clean.py PDF comparison tool"`

---

### Task 3: Integrate optional cleaning stage into Ingestion CLI

**Files:**
- Modify: `jbprag/scripts/ingest_documents.py`

- [ ] **Step 1: Edit `jbprag/scripts/ingest_documents.py` to add `--clean` parameters**
  Update the script to run PDF cleaning before feeding it to `MarkItDown`.

```python
# Replace the process_file function and main function to handle temp PDF cleaning
# Also add text clean helper
```
*(Exact replacement content will be written to `ingest_documents.py` using replace_file_content in execution)*

- [ ] **Step 2: Commit the pipeline integration**
  Run: `git add jbprag/scripts/ingest_documents.py`
  Run: `git commit -m "feat: integrate optional PDF watermark cleaner in ingest_documents"`

---

### Task 4: Create unit tests for PDF cleaner

**Files:**
- Create: `jbprag/tests/test_pdf_cleaner.py`

- [ ] **Step 1: Write mock tests in `jbprag/tests/test_pdf_cleaner.py`**
  Verify physical page coordinate math and text regular expression sanitizing functions.

- [ ] **Step 2: Run unit tests**
  Run: `PYTHONPATH=jbprag python3 -m pytest jbprag/tests/test_pdf_cleaner.py -v`
  Expected: PASS

- [ ] **Step 3: Commit unit tests**
  Run: `git add jbprag/tests/test_pdf_cleaner.py`
  Run: `git commit -m "test: add unit tests for PDF watermark cleaner"`

---

### Task 5: Full verification

- [ ] **Step 1: Run full test suite**
  Run: `PYTHONPATH=jbprag python3 -m pytest -v`
  Expected: All 211+ tests pass
