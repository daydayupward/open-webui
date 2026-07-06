import tempfile
from pathlib import Path
import pytest

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from scripts.ingest_documents import clean_text_content
from scripts.clean_pdf import clean_pdf_file

def test_clean_text_content():
    raw_text = (
        "Page 1 of 10\n"
        "Some actual content line.\n"
        "Confidential NDA Required\n"
        "TSMC NDA REQUIRED\n"
        "Another line with CONFIDENTIAL watermark text.\n"
        "Page 5"
    )
    
    cleaned = clean_text_content(raw_text, watermark="CONFIDENTIAL")
    lines = cleaned.splitlines()
    
    assert "Page 1 of 10" not in lines
    assert "Confidential NDA Required" not in lines
    assert "TSMC NDA REQUIRED" not in lines
    assert "Page 5" not in lines
    assert any("Another line with  watermark text." in l for l in lines)
    assert "Some actual content line." in lines

@pytest.mark.skipif(not PYMUPDF_AVAILABLE, reason="pymupdf not installed")
def test_clean_pdf_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.pdf"
        output_path = Path(tmpdir) / "output.pdf"
        
        doc = fitz.open()
        page = doc.new_page(width=500, height=500)
        
        # Add Stamp annotation (type 8)
        page.add_stamp_annot(fitz.Rect(100, 100, 200, 200))
        
        # Add header and footer text
        page.insert_text((10, 20), "Header Info")
        page.insert_text((10, 480), "Page 1")
        
        # Add watermark text in body
        page.insert_text((100, 250), "CONFIDENTIAL")
        page.insert_text((100, 270), "Valid body text")
        
        doc.save(input_path)
        doc.close()
        
        # Verify initial PDF has stamp annotation and texts
        doc_init = fitz.open(input_path)
        page_init = doc_init[0]
        init_annots = list(page_init.annots())
        assert len(init_annots) == 1
        assert init_annots[0].type[1] == "Stamp"
        init_text = page_init.get_text()
        assert "Header Info" in init_text
        assert "Page 1" in init_text
        assert "CONFIDENTIAL" in init_text
        assert "Valid body text" in init_text
        doc_init.close()
        
        # Run cleaner
        success = clean_pdf_file(
            input_path=input_path,
            output_path=output_path,
            header_margin=40,
            footer_margin=40,
            watermark="CONFIDENTIAL"
        )
        assert success is True
        assert output_path.exists()
        
        # Verify cleaned PDF content
        doc_clean = fitz.open(output_path)
        page_clean = doc_clean[0]
        assert len(list(page_clean.annots())) == 0
        
        cleaned_text = page_clean.get_text()
        assert "Header Info" not in cleaned_text
        assert "Page 1" not in cleaned_text
        assert "CONFIDENTIAL" not in cleaned_text
        assert "Valid body text" in cleaned_text
        
        doc_clean.close()
