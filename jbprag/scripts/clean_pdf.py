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
            try:
                annots = list(page.annots())
            except Exception:
                annots = []
            for annot in annots:
                # Stamp annotation has type name 'Stamp' (type code 13)
                if annot.type[1] == "Stamp":
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
