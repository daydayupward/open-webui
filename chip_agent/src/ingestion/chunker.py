"""Structure-aware document chunker for the chip_agent ingestion pipeline.

Splits IngestionDocument text into smaller chunks while preserving:
- Section boundaries (Markdown-style headers: #, ##, ###, etc.)
- Table structure (never splits mid-table)
- Paragraph boundaries where possible

Each chunk carries a ChunkMetadata model with positional and lineage info
so downstream indexers can reconstruct provenance.
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .loader import IngestionDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chunk model
# ---------------------------------------------------------------------------

class ChunkMetadata(BaseModel):
    """Metadata attached to every chunk produced by the chunker.

    Attributes:
        chunk_id: Deterministic SHA-256 based id (first 16 hex chars).
        source: Inherited from the parent IngestionDocument.source.
        category: Inherited from parent metadata ``category``.
        section: The nearest header/section the chunk belongs to (if any).
        position: Zero-based index of this chunk within the parent document.
        total_chunks: Total number of chunks produced from the parent doc.
        parent_metadata: The full metadata dict of the parent document.
    """

    chunk_id: str
    source: Optional[str] = None
    category: Optional[str] = None
    section: Optional[str] = None
    position: int = 0
    total_chunks: int = 1
    parent_metadata: Dict[str, Any] = Field(default_factory=dict)


class TextChunk(BaseModel):
    """A chunk of text produced by the chunker along with its metadata."""

    text: str
    metadata: ChunkMetadata


# ---------------------------------------------------------------------------
# Internal helpers – text block detection
# ---------------------------------------------------------------------------

# Regex patterns for Markdown-style headers (ATX headers)
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# A table block is detected by consecutive lines that contain a pipe character
# followed by at least one more pipe on the same line.  We also require at least
# a separator row (|---|---|) to confirm it is a real table.
_TABLE_START_RE = re.compile(r"^\|.+\|$", re.MULTILINE)
_TABLE_SEP_RE = re.compile(r"^\|[-| :]+\|$", re.MULTILINE)


def _classify_blocks(text: str) -> List[Dict[str, Any]]:
    """Split *text* into classified blocks: ``header``, ``table``, or ``paragraph``.

    Returns a list of dicts ``{"type": str, "text": str, "header": str | None}``.
    The ``header`` field carries the most recent header title that applies to
    the block (for downstream section tracking).
    """
    lines = text.split("\n")
    blocks: List[Dict[str, Any]] = []
    current_header: Optional[str] = None
    buf: List[str] = []
    buf_type: str = "paragraph"

    def _flush():
        nonlocal buf
        joined = "\n".join(buf).strip()
        if joined:
            blocks.append({"type": buf_type, "text": joined, "header": current_header})
        buf = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # --- Header detection ---
        hdr_match = _HEADER_RE.match(line)
        if hdr_match:
            _flush()
            current_header = hdr_match.group(2).strip()
            blocks.append(
                {"type": "header", "text": line.strip(), "header": current_header}
            )
            i += 1
            continue

        # --- Table detection ---
        if _TABLE_START_RE.match(line):
            # Gather all consecutive table lines
            table_lines: List[str] = []
            while i < len(lines) and _TABLE_START_RE.match(lines[i]):
                table_lines.append(lines[i])
                i += 1
            # Only treat as table if there is a separator row (|---|---|)
            table_text = "\n".join(table_lines)
            if _TABLE_SEP_RE.search(table_text):
                _flush()
                blocks.append(
                    {"type": "table", "text": table_text, "header": current_header}
                )
                continue
            else:
                # Not a real table – treat as paragraph
                buf.extend(table_lines)
                buf_type = "paragraph"
                continue

        # --- Regular paragraph line ---
        if line.strip() == "":
            _flush()
            buf_type = "paragraph"
            i += 1
            continue

        buf.append(line)
        buf_type = "paragraph"
        i += 1

    _flush()
    return blocks


# ---------------------------------------------------------------------------
# Core chunking logic
# ---------------------------------------------------------------------------

def _generate_chunk_id(doc: IngestionDocument, position: int) -> str:
    """Generate a deterministic chunk id from document source + text + position."""
    seed = f"{doc.source or ''}:{doc.text[:200]}:{position}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _split_long_paragraph(
    text: str,
    max_chars: int,
) -> List[str]:
    """Split a paragraph that exceeds *max_chars* into sub-chunks on sentence
    boundaries.  Falls back to hard character split if no sentence boundary is
    found within the limit.
    """
    if len(text) <= max_chars:
        return [text]

    # Try to split on sentence boundaries (. ! ? followed by space or end)
    sentence_re = re.compile(r"(?<=[.!?])\s+")
    sentences = sentence_re.split(text)

    chunks: List[str] = []
    current = ""
    for sent in sentences:
        candidate = f"{current} {sent}".strip() if current else sent
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If a single sentence is still too long, hard-split it
            while len(sent) > max_chars:
                chunks.append(sent[:max_chars])
                sent = sent[max_chars:]
            current = sent
    if current:
        chunks.append(current)

    return chunks


def chunk_document(
    doc: IngestionDocument,
    max_chunk_chars: int = 2000,
    overlap_chars: int = 500,
) -> List[TextChunk]:
    """Chunk a single :class:`IngestionDocument` into :class:`TextChunk` objects.

    The algorithm:

    1. Classify the document text into *header*, *table*, and *paragraph* blocks.
    2. Each block becomes one or more chunks, subject to *max_chunk_chars*.
    3. Tables are **never** split mid-row.  If a table exceeds the limit it is
       kept as a single oversized chunk (logged as a warning).
    4. Paragraphs that exceed the limit are split on sentence boundaries.
    5. Optionally, *overlap_chars* characters of context from the previous chunk
       are prepended to the next chunk.

    Args:
        doc: The source document.
        max_chunk_chars: Target maximum characters per chunk.  Hard tables may
            exceed this.
        overlap_chars: Number of trailing characters from the previous chunk to
            prepend to the next chunk (useful for retrieval context).

    Returns:
        A list of :class:`TextChunk` objects.
    """
    if not doc.text.strip():
        return []

    blocks = _classify_blocks(doc.text)
    if not blocks:
        return []

    # Build preliminary chunk texts
    raw_chunks: List[Dict[str, Any]] = []  # {"text": str, "section": str|None}

    for block in blocks:
        btype = block["type"]
        btext = block["text"]
        section = block.get("header")

        if btype == "header":
            # Headers become their own small chunk (useful for section indexing)
            raw_chunks.append({"text": btext, "section": section})

        elif btype == "table":
            if len(btext) > max_chunk_chars:
                logger.warning(
                    "Table in section %r exceeds max_chunk_chars (%d > %d); "
                    "keeping as single chunk to preserve structure.",
                    section,
                    len(btext),
                    max_chunk_chars,
                )
            raw_chunks.append({"text": btext, "section": section})

        else:  # paragraph
            sub_parts = _split_long_paragraph(btext, max_chunk_chars)
            for part in sub_parts:
                raw_chunks.append({"text": part, "section": section})

    # Apply overlap: prepend trailing chars from previous chunk
    if overlap_chars > 0 and len(raw_chunks) > 1:
        overlapped: List[Dict[str, Any]] = [raw_chunks[0]]
        for idx in range(1, len(raw_chunks)):
            prev_text = raw_chunks[idx - 1]["text"]
            prefix = prev_text[-overlap_chars:]
            overlapped.append(
                {
                    "text": f"{prefix} ... {raw_chunks[idx]['text']}",
                    "section": raw_chunks[idx]["section"],
                }
            )
        raw_chunks = overlapped

    # Assign chunk metadata
    total = len(raw_chunks)
    chunks: List[TextChunk] = []
    for idx, rc in enumerate(raw_chunks):
        chunk_id = _generate_chunk_id(doc, idx)
        meta = ChunkMetadata(
            chunk_id=chunk_id,
            source=doc.source,
            category=doc.metadata.get("category"),
            section=rc["section"],
            position=idx,
            total_chunks=total,
            parent_metadata=doc.metadata,
        )
        chunks.append(TextChunk(text=rc["text"], metadata=meta))

    return chunks


def chunk_documents(
    docs: List[IngestionDocument],
    max_chunk_chars: int = 1000,
    overlap_chars: int = 0,
) -> List[TextChunk]:
    """Chunk a list of documents and return a flat list of chunks.

    Args:
        docs: Documents to chunk.
        max_chunk_chars: Target maximum characters per chunk.
        overlap_chars: Characters of overlap between consecutive chunks.

    Returns:
        A flat list of all chunks across all documents.
    """
    all_chunks: List[TextChunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, max_chunk_chars, overlap_chars))
    logger.info(
        "Produced %d chunks from %d documents", len(all_chunks), len(docs)
    )
    return all_chunks
