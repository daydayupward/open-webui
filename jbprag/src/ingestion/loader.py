"""Document loader for PDK, EDA manual, and project document JSONL files.

Loads documents from JSONL seed data and outputs unified IngestionDocument
objects that can be consumed by the chunking and indexing pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unified document model
# ---------------------------------------------------------------------------

class IngestionDocument(BaseModel):
    """A single document loaded from any source type (PDK, EDA, Project).

    Attributes:
        text: The raw text content of the document.
        metadata: Arbitrary metadata dict.  Always contains at least
            ``category`` (one of ``PDK``, ``EDA``, ``Project_Doc``).
        source: The file path the document was loaded from.
    """

    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------

def _parse_jsonl_line(line: str, source: str, line_no: int) -> Optional[IngestionDocument]:
    """Parse a single JSONL line into an IngestionDocument.

    Returns ``None`` and logs a warning when the line cannot be parsed or is
    missing required fields.
    """
    line = line.strip()
    if not line:
        return None

    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        logger.warning("Skipping malformed JSON at %s:%d: %s", source, line_no, exc)
        return None

    text = data.get("text")
    if not text or not isinstance(text, str):
        logger.warning("Skipping entry without 'text' at %s:%d", source, line_no)
        return None

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        logger.warning(
            "Skipping entry with non-dict metadata at %s:%d", source, line_no
        )
        return None

    return IngestionDocument(text=text, metadata=metadata, source=source)


def load_jsonl(path: str | Path) -> List[IngestionDocument]:
    """Load all documents from a single JSONL file.

    Args:
        path: Path to the ``.jsonl`` file.

    Returns:
        A list of :class:`IngestionDocument` instances.  Malformed lines are
        skipped with a warning.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    documents: List[IngestionDocument] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            doc = _parse_jsonl_line(line, source=str(path), line_no=line_no)
            if doc is not None:
                documents.append(doc)

    logger.info("Loaded %d documents from %s", len(documents), path)
    return documents


# ---------------------------------------------------------------------------
# High-level loaders per source type
# ---------------------------------------------------------------------------

def load_pdk_rules(path: str | Path) -> List[IngestionDocument]:
    """Load PDK rules from a JSONL file.

    Each document's metadata should contain ``category == "PDK"``.
    """
    docs = load_jsonl(path)
    _validate_category(docs, expected="PDK", source=str(path))
    return docs


def load_eda_manuals(path: str | Path) -> List[IngestionDocument]:
    """Load EDA manual entries from a JSONL file.

    Each document's metadata should contain ``category == "EDA"``.
    """
    docs = load_jsonl(path)
    _validate_category(docs, expected="EDA", source=str(path))
    return docs


def load_project_docs(path: str | Path) -> List[IngestionDocument]:
    """Load project documents from a JSONL file.

    Each document's metadata should contain ``category == "Project_Doc"``.
    """
    docs = load_jsonl(path)
    _validate_category(docs, expected="Project_Doc", source=str(path))
    return docs


def load_all_documents(
    pdk_path: str | Path,
    eda_path: str | Path,
    project_path: str | Path,
) -> List[IngestionDocument]:
    """Load documents from all three source files and return a merged list.

    Args:
        pdk_path: Path to PDK rules JSONL file.
        eda_path: Path to EDA manuals JSONL file.
        project_path: Path to project docs JSONL file.

    Returns:
        Combined list of all loaded documents.
    """
    all_docs: List[IngestionDocument] = []
    all_docs.extend(load_pdk_rules(pdk_path))
    all_docs.extend(load_eda_manuals(eda_path))
    all_docs.extend(load_project_docs(project_path))
    logger.info("Loaded %d total documents from all sources", len(all_docs))
    return all_docs


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_category(
    docs: List[IngestionDocument],
    expected: str,
    source: str,
) -> None:
    """Log a warning if any document lacks the expected category."""
    for i, doc in enumerate(docs, start=1):
        actual = doc.metadata.get("category")
        if actual != expected:
            logger.warning(
                "Document %d in %s has category=%r, expected %r",
                i,
                source,
                actual,
                expected,
            )
