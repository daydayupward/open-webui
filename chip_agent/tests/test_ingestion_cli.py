import sys
from unittest.mock import MagicMock
# Mock the entire markitdown module to avoid import error during tests
sys.modules['markitdown'] = MagicMock()

import pytest
from unittest.mock import patch
from pathlib import Path
from scripts.ingest_documents import parse_args, process_file

@patch("sys.argv", ["ingest_documents.py", "-f", "dummy.pdf", "-c", "PDK", "-n", "N5", "-t", "Innovus"])
def test_parse_args():
    args = parse_args()
    assert args.file == "dummy.pdf"
    assert args.categories == "PDK"
    assert args.node == "N5"
    assert args.tool == "Innovus"
    assert args.reset is False

@patch("scripts.ingest_documents.chunk_document")
def test_process_file_success(mock_chunk_document):
    # Setup MarkItDown mock
    import markitdown
    mock_md_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.text_content = "This is sample PDK text about N5 metal pitch."
    mock_md_instance.convert.return_value = mock_result
    markitdown.MarkItDown.return_value = mock_md_instance

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
