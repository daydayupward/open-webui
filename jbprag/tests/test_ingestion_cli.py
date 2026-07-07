import sys
from unittest.mock import MagicMock, patch
from pathlib import Path

# Mock modules to avoid import/execution dependencies during tests
sys.modules['markitdown'] = MagicMock()
sys.modules['pymupdf4llm'] = MagicMock()

import pytest
from scripts.ingest_documents import parse_args, process_file

@patch("sys.argv", ["ingest_documents.py", "-f", "dummy.pdf", "-c", "PDK", "-n", "N5", "-t", "Innovus"])
def test_parse_args():
    args = parse_args()
    assert args.file == "dummy.pdf"
    assert args.category == "PDK"
    assert args.node == "N5"
    assert args.tool == "Innovus"
    assert args.reset is False

@patch("scripts.ingest_documents.chunk_document")
def test_process_pdf_file_success(mock_chunk_document):
    import pymupdf4llm
    pymupdf4llm.to_markdown.reset_mock()
    pymupdf4llm.to_markdown.return_value = "This is sample PDK text about N5 metal pitch."

    mock_chunk_document.return_value = ["chunk1", "chunk2"]

    class ArgsMock:
        category = "PDK"
        node = "N5"
        tool = "Innovus"
        project_id = None
        clean = False

    chunks = process_file(Path("test.pdf"), ArgsMock())
    assert chunks == ["chunk1", "chunk2"]
    pymupdf4llm.to_markdown.assert_called_once_with(str(Path("test.pdf").absolute()))

@patch("scripts.ingest_documents.chunk_document")
def test_process_office_file_success(mock_chunk_document):
    import markitdown
    markitdown.MarkItDown.reset_mock()
    mock_md_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.text_content = "Sample Office document content."
    mock_md_instance.convert.return_value = mock_result
    markitdown.MarkItDown.return_value = mock_md_instance

    mock_chunk_document.return_value = ["chunk1", "chunk2"]

    class ArgsMock:
        category = "EDA"
        node = "N5"
        tool = "Innovus"
        project_id = None
        clean = False

    chunks = process_file(Path("test.docx"), ArgsMock())
    assert chunks == ["chunk1", "chunk2"]
    mock_md_instance.convert.assert_called_once_with(str(Path("test.docx").absolute()))
