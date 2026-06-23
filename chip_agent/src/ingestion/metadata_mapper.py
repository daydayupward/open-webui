"""Unified metadata mapper for the chip_agent ingestion pipeline.

Normalises and merges metadata from :class:`IngestionDocument` and
:class:`TextChunk` into a flat, consistent ``ChunkIndexMetadata`` dict
ready for vector-store indexing.

Unified output fields
---------------------
doc_id, chunk_id, category, node, tool, project_id, source, section, page, updated_at
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .chunker import ChunkMetadata, TextChunk
from .loader import IngestionDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid values for categorical fields
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "PDK",
    "StdCell",
    "SRAM",
    "IP",
    "EDA",
    "Platform_Flow",
    "Project_Doc",
    "Script",
    "Literature",
}

VALID_NODES = {"N5", "N7"}

VALID_TOOLS = {"Innovus", "ICC2", "Calibre", "PrimeTime"}

VALID_PROJECT_IDS = {"Proj_A", "Proj_B"}

VALID_VENDORS = {"Synopsys", "Cadence", "Innosilicon", "Alphawave", "TSMC"}

# ---------------------------------------------------------------------------
# Unified index metadata model
# ---------------------------------------------------------------------------


class ChunkIndexMetadata(BaseModel):
    """Flat metadata attached to every chunk going into the vector store.

    All fields are present on every indexed chunk so that retrieval filters
    can rely on a consistent schema.
    """

    doc_id: str = Field(..., description="Deterministic document-level id.")
    chunk_id: str = Field(..., description="Deterministic chunk-level id from chunker.")
    category: Optional[str] = Field(None, description="Document category: PDK, EDA, Project_Doc, General, IP.")
    vendor: Optional[str] = Field(None, description="IP vendor, e.g., Synopsys, Cadence, TSMC.")
    node: Optional[str] = Field(None, description="Process node, e.g. N5, N7.")
    tool: Optional[str] = Field(None, description="EDA tool, e.g. Innovus, ICC2.")
    project_id: Optional[str] = Field(None, description="Project identifier, e.g. Proj_A.")
    source: Optional[str] = Field(None, description="Originating file path.")
    section: Optional[str] = Field(None, description="Section header the chunk belongs to.")
    page: Optional[int] = Field(None, description="Page number if available.")
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of when this metadata was created.",
    )


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def _normalize_category(value: Optional[str]) -> Optional[str]:
    """Normalise a category string to one of the canonical values."""
    if not value:
        return None
    lower = value.strip().lower()
    mapping = {
        "pdk": "PDK",
        "process": "PDK",
        "foundry": "PDK",
        "foundry_doc": "PDK",
        "foundry_manual": "PDK",
        "stdcell": "StdCell",
        "standard_cell": "StdCell",
        "liberty": "StdCell",
        "lib": "StdCell",
        "sram": "SRAM",
        "memory": "SRAM",
        "macro": "SRAM",
        "platform": "Platform_Flow",
        "flow": "Platform_Flow",
        "methodology": "Platform_Flow",
        "platform_flow": "Platform_Flow",
        "checklist_template": "Platform_Flow",
        "signoff_template": "Platform_Flow",
        "script": "Script",
        "tcl": "Script",
        "python": "Script",
        "makefile": "Script",
        "csh": "Script",
        "sh": "Script",
        "literature": "Literature",
        "paper": "Literature",
        "book": "Literature",
        "textbook": "Literature",
        "general": "Literature",
        "training": "Literature",
        "team": "Literature",
        "project_doc": "Project_Doc",
        "project": "Project_Doc",
        "doc": "Project_Doc",
        "checklist_result": "Project_Doc",
        "project_checklist": "Project_Doc",
        "ip": "IP",
        "ip_doc": "IP",
        "datasheet": "IP",
        "manual": "IP",
        "eda": "EDA",
        "tool": "EDA",
        "command": "EDA",
    }
    return mapping.get(lower, value.strip())


def _normalize_node(value: Optional[str]) -> Optional[str]:
    """Normalise a process-node string."""
    if not value:
        return None
    upper = value.strip().upper()
    mapping = {
        "N5": "N5",
        "5NM": "N5",
        "5": "N5",
        "N7": "N7",
        "7NM": "N7",
        "7": "N7",
    }
    return mapping.get(upper, value.strip())


def _normalize_tool(value: Optional[str]) -> Optional[str]:
    """Normalise an EDA tool string."""
    if not value:
        return None
    lower = value.strip().lower()
    mapping = {
        "innovus": "Innovus",
        "encounter": "Innovus",
        "icc2": "ICC2",
        "icc": "ICC2",
        "ic compiler": "ICC2",
        "calibre": "Calibre",
        "primetime": "PrimeTime",
        "pt": "PrimeTime",
    }
    canonical = mapping.get(lower)
    if canonical:
        return canonical
    return value.strip().capitalize()


def _normalize_project_id(value: Optional[str]) -> Optional[str]:
    """Normalise a project-id string."""
    if not value:
        return None
    collapsed = value.strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    if "proja" in collapsed or "projecta" in collapsed:
        return "Proj_A"
    if "projb" in collapsed or "projectb" in collapsed:
        return "Proj_B"
    return value.strip()


def _normalize_vendor(value: Optional[str]) -> Optional[str]:
    """Normalise an IP vendor string."""
    if not value:
        return None
    lower = value.strip().lower()
    mapping = {
        "synopsys": "Synopsys",
        "snps": "Synopsys",
        "cadence": "Cadence",
        "cdns": "Cadence",
        "innosilicon": "Innosilicon",
        "alphawave": "Alphawave",
        "tsmc": "TSMC",
    }
    canonical = mapping.get(lower)
    if canonical:
        return canonical
    return value.strip().capitalize()


def _generate_doc_id(source: Optional[str], text_prefix: str) -> str:
    """Generate a deterministic doc_id from the document source and text prefix."""
    seed = f"{source or ''}:{text_prefix[:200]}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Core public API
# ---------------------------------------------------------------------------


def normalize_metadata_fields(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise and validate the categorical metadata fields *in-place*.

    Applies canonical casing / aliasing to ``category``, ``node``, ``tool``,
    and ``project_id``.  Unknown values are kept as-is with a warning.

    Args:
        metadata: A mutable metadata dict (modified in-place and returned).

    Returns:
        The same dict, with normalised values.
    """
    if "category" in metadata:
        original = metadata["category"]
        normalised = _normalize_category(original)
        if normalised and normalised not in VALID_CATEGORIES:
            logger.warning("Unknown category %r after normalisation; keeping as-is.", normalised)
        metadata["category"] = normalised

    if "node" in metadata:
        original = metadata["node"]
        normalised = _normalize_node(original)
        if normalised and normalised not in VALID_NODES:
            logger.warning("Unknown node %r after normalisation; keeping as-is.", normalised)
        metadata["node"] = normalised

    if "tool" in metadata:
        original = metadata["tool"]
        normalised = _normalize_tool(original)
        if normalised and normalised not in VALID_TOOLS:
            logger.warning("Unknown tool %r after normalisation; keeping as-is.", normalised)
        metadata["tool"] = normalised

    if "project_id" in metadata:
        original = metadata["project_id"]
        normalised = _normalize_project_id(original)
        if normalised and normalised not in VALID_PROJECT_IDS:
            logger.warning(
                "Unknown project_id %r after normalisation; keeping as-is.",
                normalised,
            )
        metadata["project_id"] = normalised

    if "vendor" in metadata:
        original = metadata["vendor"]
        normalised = _normalize_vendor(original)
        if normalised and normalised not in VALID_VENDORS:
            logger.warning("Unknown vendor %r after normalisation; keeping as-is.", normalised)
        metadata["vendor"] = normalised

    return metadata


def merge_metadata(chunk: TextChunk, doc: Optional[IngestionDocument] = None) -> ChunkIndexMetadata:
    """Merge chunk metadata with document metadata into a unified index record.

    The merge priority is:
    1. Chunk-level metadata (``chunk_id``, ``section``, ``source``) from the chunker.
    2. Document-level metadata (``category``, ``node``, ``tool``, ``project_id``)
       from the parent document's metadata dict.
    3. Derived fields (``doc_id``, ``updated_at``) are generated.

    Args:
        chunk: A :class:`TextChunk` produced by the chunker.
        doc: The original :class:`IngestionDocument`.  If ``None``, the
            chunk's ``parent_metadata`` is used as the document metadata
            and ``doc_id`` is derived from the chunk's source.

    Returns:
        A fully-populated :class:`ChunkIndexMetadata` instance.
    """
    chunk_meta: ChunkMetadata = chunk.metadata

    # Resolve the document metadata dict
    if doc is not None:
        doc_meta: Dict[str, Any] = dict(doc.metadata)
        doc_source = doc.source
        doc_text_prefix = doc.text
    else:
        doc_meta = dict(chunk_meta.parent_metadata)
        doc_source = chunk_meta.source
        doc_text_prefix = chunk.text

    # Normalise categorical fields from the document metadata
    normalize_metadata_fields(doc_meta)

    # Also normalise category that may have been set on the chunk metadata
    chunk_category = _normalize_category(chunk_meta.category)

    # Build the unified record -- chunk-level fields take precedence for
    # chunk-specific data; document-level fields fill in the rest.
    doc_id = _generate_doc_id(doc_source, doc_text_prefix)

    # Resolve page: look for 'page' in the document metadata
    page = doc_meta.get("page")
    if page is not None:
        try:
            page = int(page)
        except (TypeError, ValueError):
            logger.warning("Non-integer page value %r in metadata; setting to None.", page)
            page = None

    return ChunkIndexMetadata(
        doc_id=doc_id,
        chunk_id=chunk_meta.chunk_id,
        category=chunk_category or doc_meta.get("category"),
        node=doc_meta.get("node"),
        tool=doc_meta.get("tool"),
        project_id=doc_meta.get("project_id"),
        vendor=doc_meta.get("vendor"),
        source=chunk_meta.source,
        section=chunk_meta.section,
        page=page,
    )


def map_chunks(
    chunks: list[TextChunk],
    doc: Optional[IngestionDocument] = None,
) -> list[ChunkIndexMetadata]:
    """Map a list of chunks to unified index metadata.

    This is the high-level entry point for the metadata mapping step of the
    ingestion pipeline.

    Args:
        chunks: List of :class:`TextChunk` from the chunker.
        doc: The parent :class:`IngestionDocument`.  When ``None``, each
            chunk's own ``parent_metadata`` is used.

    Returns:
        A list of :class:`ChunkIndexMetadata`, one per input chunk.
    """
    results: list[ChunkIndexMetadata] = []
    for chunk in chunks:
        results.append(merge_metadata(chunk, doc))
    logger.info("Mapped metadata for %d chunks.", len(results))
    return results
