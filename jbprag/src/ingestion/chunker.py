"""Structure-aware document chunker for the jbprag ingestion pipeline.

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
import tiktoken

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
    max_tokens: int,
    encoder: tiktoken.Encoding,
) -> List[str]:
    """Split a paragraph that exceeds *max_tokens* into sub-chunks on sentence
    boundaries.  Falls back to hard token split if no sentence boundary is
    found within the limit.
    """
    if len(encoder.encode(text)) <= max_tokens:
        return [text]

    # Try to split on sentence boundaries (. ! ? followed by space or end)
    sentence_re = re.compile(r"(?<=[.!?])\s+")
    sentences = sentence_re.split(text)

    chunks: List[str] = []
    current = ""
    for sent in sentences:
        candidate = f"{current} {sent}".strip() if current else sent
        if len(encoder.encode(candidate)) <= max_tokens:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # If a single sentence is still too long, hard-split it by tokens
            sent_tokens = encoder.encode(sent)
            while len(sent_tokens) > max_tokens:
                chunks.append(encoder.decode(sent_tokens[:max_tokens]))
                sent_tokens = sent_tokens[max_tokens:]
            current = encoder.decode(sent_tokens)
    if current:
        chunks.append(current)

    return chunks


def merge_into_parent_chunks(
    blocks: List[Dict[str, Any]],
    max_parent_tokens: int,
    overlap_tokens: int,
    encoder
) -> List[Dict[str, Any]]:
    parent_chunks = []
    current_section = None
    current_blocks = []
    current_tokens = 0

    for block in blocks:
        btext = block["text"]
        btokens = len(encoder.encode(btext))
        
        # Greedy merger: merge blocks until max_parent_tokens is exceeded
        if current_tokens + btokens > max_parent_tokens and current_blocks:
            text = "\n\n".join(b["text"] for b in current_blocks)
            parent_chunks.append({"text": text, "section": current_section})
            current_blocks = []
            current_tokens = 0
            
        current_blocks.append(block)
        current_tokens += btokens
        if block.get("header"):
            current_section = block["header"]

    if current_blocks:
        text = "\n\n".join(b["text"] for b in current_blocks)
        parent_chunks.append({"text": text, "section": current_section})

    # Apply overlap to parent chunks
    if overlap_tokens > 0 and len(parent_chunks) > 1:
        overlapped = [parent_chunks[0]]
        for idx in range(1, len(parent_chunks)):
            prev_text = parent_chunks[idx - 1]["text"]
            prev_tokens = encoder.encode(prev_text)
            prefix = encoder.decode(prev_tokens[-overlap_tokens:]) if len(prev_tokens) > overlap_tokens else prev_text
            overlapped.append(
                {
                    "text": f"{prefix} ... {parent_chunks[idx]['text']}",
                    "section": parent_chunks[idx]["section"],
                }
            )
        parent_chunks = overlapped

    return parent_chunks


def split_parent_into_children(
    parent_text: str,
    max_child_tokens: int,
    child_overlap_tokens: int,
    encoder
) -> List[str]:
    tokens = encoder.encode(parent_text)
    if len(tokens) <= max_child_tokens:
        return [parent_text]

    children = []
    idx = 0
    while idx < len(tokens):
        end = min(idx + max_child_tokens, len(tokens))
        child_text = encoder.decode(tokens[idx:end])
        children.append(child_text)
        if end == len(tokens):
            break
        idx += (max_child_tokens - child_overlap_tokens)
    return children


def chunk_document(
    doc: IngestionDocument,
    max_chunk_tokens: int = 2000,
    overlap_tokens: int = 500,
) -> List[TextChunk]:
    """Chunk a single :class:`IngestionDocument` into parent-child :class:`TextChunk` objects.
    
    1. Parent Chunk size is max_chunk_tokens (2000 tokens) with overlap_tokens (500 tokens).
    2. Child Chunk size is ~300 tokens, embedding parent_text in its metadata.
    3. Option 2: Image nodes are colocated within their respective parent chunks.
    """
    if not doc.text.strip():
        return []

    blocks = _classify_blocks(doc.text)
    if not blocks:
        return []

    try:
        encoder = tiktoken.encoding_for_model("gpt-4o")
    except KeyError:
        encoder = tiktoken.get_encoding("cl100k_base")

    # Pre-split extremely long blocks to avoid overflowing parent limit
    pre_split_blocks = []
    for block in blocks:
        if block["type"] == "paragraph" and len(encoder.encode(block["text"])) > max_chunk_tokens:
            sub_parts = _split_long_paragraph(block["text"], max_chunk_tokens, encoder)
            for part in sub_parts:
                pre_split_blocks.append({"type": "paragraph", "text": part, "header": block.get("header")})
        else:
            pre_split_blocks.append(block)

    parent_chunks = merge_into_parent_chunks(pre_split_blocks, max_chunk_tokens, overlap_tokens, encoder)

    chunks: List[TextChunk] = []
    raw_children = []
    for rc in parent_chunks:
        parent_text = rc["text"]
        # Split parent into children chunks of size 300 tokens, 50 tokens overlap
        children_texts = split_parent_into_children(parent_text, 300, 50, encoder)
        for child_text in children_texts:
            raw_children.append({
                "child_text": child_text,
                "parent_text": parent_text,
                "section": rc["section"]
            })

    total = len(raw_children)
    for idx, child_data in enumerate(raw_children):
        chunk_id = _generate_chunk_id(doc, idx)
        meta = ChunkMetadata(
            chunk_id=chunk_id,
            source=doc.source,
            category=doc.metadata.get("category"),
            section=child_data["section"],
            position=idx,
            total_chunks=total,
            parent_metadata={
                **doc.metadata,
                "parent_text": child_data["parent_text"]
            }
        )
        chunks.append(TextChunk(text=child_data["child_text"], metadata=meta))

    return chunks


def chunk_documents(
    docs: List[IngestionDocument],
    max_chunk_tokens: int = 2000,
    overlap_tokens: int = 500,
) -> List[TextChunk]:
    """Chunk a list of documents and return a flat list of chunks.

    Args:
        docs: Documents to chunk.
        max_chunk_tokens: Target maximum tokens per chunk.
        overlap_tokens: Tokens of overlap between consecutive chunks.

    Returns:
        A flat list of all chunks across all documents.
    """
    all_chunks: List[TextChunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, max_chunk_tokens, overlap_tokens))
    logger.info(
        "Produced %d chunks from %d documents", len(all_chunks), len(docs)
    )
    return all_chunks
