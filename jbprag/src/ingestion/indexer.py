"""Vector store indexer for the jbprag ingestion pipeline.

Handles embedding generation, upsert operations, and incremental updates
to ensure duplicate imports do not create dirty duplicates in the vector store.

The indexer uses deterministic chunk_ids from the metadata to perform
upserts (update-if-exists, insert-if-not) rather than blind inserts.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector

from ..vector_store import get_vector_store
from .chunker import TextChunk
from .metadata_mapper import ChunkIndexMetadata, map_chunks

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Core indexing functions
# ---------------------------------------------------------------------------


def _build_document(chunk: TextChunk, meta: ChunkIndexMetadata) -> Document:
    """Convert a TextChunk + metadata into a langchain Document for indexing.

    The chunk_id is stored in the document metadata so it can be used for
    deduplication during upsert operations.
    """
    return Document(
        page_content=chunk.text,
        metadata={
            "chunk_id": meta.chunk_id,
            "doc_id": meta.doc_id,
            "category": meta.category,
            "node": meta.node,
            "tool": meta.tool,
            "project_id": meta.project_id,
            "source": meta.source,
            "section": meta.section,
            "page": meta.page,
            "parent_text": meta.parent_text,
            "updated_at": meta.updated_at,
        },
    )


def _deduplicate_chunks(
    chunks: List[TextChunk],
    metadatas: List[ChunkIndexMetadata],
) -> tuple[List[TextChunk], List[ChunkIndexMetadata]]:
    """Remove duplicate chunks based on chunk_id, keeping the last occurrence.

    This ensures that if the same chunk appears multiple times in a batch
    (e.g., from re-ingestion), only the latest version is indexed.

    Returns:
        Tuple of (deduplicated chunks, deduplicated metadatas).
    """
    seen: Dict[str, int] = {}
    for idx, meta in enumerate(metadatas):
        seen[meta.chunk_id] = idx

    # Preserve order of last occurrences
    unique_indices = sorted(seen.values())
    deduped_chunks = [chunks[i] for i in unique_indices]
    deduped_metas = [metadatas[i] for i in unique_indices]

    removed = len(chunks) - len(deduped_chunks)
    if removed > 0:
        logger.info("Deduplicated %d chunks (kept %d unique).", removed, len(deduped_chunks))

    return deduped_chunks, deduped_metas


def index_chunks(
    chunks: List[TextChunk],
    connection_string: str,
    collection_name: str,
    embeddings: Embeddings,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Dict[str, Any]:
    """Index a list of TextChunks into the vector store with upsert semantics.

    This is the main entry point for the indexing step. It:
    1. Maps chunk metadata to unified ChunkIndexMetadata.
    2. Deduplicates chunks by chunk_id within the batch.
    3. Converts chunks to langchain Documents.
    4. Upserts documents into the PGVector store in batches.

    The upsert behavior ensures that:
    - New chunks are inserted.
    - Existing chunks (same chunk_id) are updated with new content/metadata.
    - Re-ingestion of the same documents does not create duplicates.

    Args:
        chunks: List of TextChunk objects from the chunker.
        connection_string: PostgreSQL connection string.
        collection_name: Name of the vector store collection.
        embeddings: Embeddings model instance.
        batch_size: Number of documents to upsert per batch.

    Returns:
        Dict with indexing statistics:
        - total_input: Total chunks received.
        - after_dedup: Chunks after deduplication.
        - indexed: Chunks successfully indexed.
        - batches: Number of batches processed.
    """
    if not chunks:
        logger.info("No chunks to index.")
        return {"total_input": 0, "after_dedup": 0, "indexed": 0, "batches": 0}

    total_input = len(chunks)

    # Step 1: Map metadata
    metadatas = map_chunks(chunks)

    # Step 2: Deduplicate within batch
    chunks, metadatas = _deduplicate_chunks(chunks, metadatas)
    after_dedup = len(chunks)

    # Step 3: Build langchain Documents
    documents = [_build_document(c, m) for c, m in zip(chunks, metadatas)]

    # Step 4: Get vector store and upsert in batches
    store = get_vector_store(connection_string, collection_name, embeddings)

    indexed = 0
    batch_count = 0
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        batch_count += 1

        try:
            # PGVector.add_documents with ids performs upsert:
            # if a document with the same id exists, it is updated.
            ids = [doc.metadata["chunk_id"] for doc in batch]
            store.add_documents(batch, ids=ids)
            indexed += len(batch)
            logger.debug(
                "Indexed batch %d: %d documents.", batch_count, len(batch)
            )
        except Exception as exc:
            logger.error(
                "Failed to index batch %d (%d documents): %s",
                batch_count,
                len(batch),
                exc,
            )
            raise RuntimeError(
                f"Indexing failed at batch {batch_count}: {exc}"
            ) from exc

    stats = {
        "total_input": total_input,
        "after_dedup": after_dedup,
        "indexed": indexed,
        "batches": batch_count,
    }
    logger.info(
        "Indexing complete: %d input -> %d after dedup -> %d indexed in %d batches.",
        stats["total_input"],
        stats["after_dedup"],
        stats["indexed"],
        stats["batches"],
    )
    return stats


def delete_by_doc_id(
    doc_id: str,
    connection_string: str,
    collection_name: str,
    embeddings: Embeddings,
) -> int:
    """Delete all chunks belonging to a document from the vector store.

    This is useful for full re-ingestion of a document: delete old chunks
    first, then re-index the new version.

    Args:
        doc_id: The document-level id whose chunks should be removed.
        connection_string: PostgreSQL connection string.
        collection_name: Name of the vector store collection.
        embeddings: Embeddings model instance.

    Returns:
        Number of chunks deleted.
    """
    store = get_vector_store(connection_string, collection_name, embeddings)

    try:
        # Use the filter to find all chunks for this doc_id
        # PGVector supports deletion by filter
        store.delete(filter={"doc_id": doc_id})
        logger.info("Deleted chunks for doc_id=%s.", doc_id)
        # Note: PGVector.delete doesn't return count; we return 0 as indicator
        return 0
    except Exception as exc:
        logger.error("Failed to delete chunks for doc_id=%s: %s", doc_id, exc)
        raise RuntimeError(f"Deletion failed for doc_id={doc_id}: {exc}") from exc


def get_indexed_chunk_ids(
    connection_string: str,
    collection_name: str,
    embeddings: Embeddings,
    doc_id: Optional[str] = None,
) -> List[str]:
    """Retrieve chunk_ids currently in the vector store.

    Useful for incremental indexing: compare against new chunks to determine
    which need to be updated vs. inserted.

    Args:
        connection_string: PostgreSQL connection string.
        collection_name: Name of the vector store collection.
        embeddings: Embeddings model instance.
        doc_id: If provided, only return chunk_ids for this document.

    Returns:
        List of chunk_id strings currently indexed.
    """
    from sqlalchemy import create_engine, text

    try:
        engine = create_engine(connection_string)
        query = """
            SELECT cmetadata->>'chunk_id'
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = :collection
        """
        params = {"collection": collection_name}
        
        if doc_id:
            query += " AND cmetadata->>'doc_id' = :doc_id"
            params["doc_id"] = doc_id
            
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            chunk_ids = [row[0] for row in result if row[0]]
            
        logger.info("Found %d indexed chunk_ids.", len(chunk_ids))
        return chunk_ids
    except Exception as exc:
        logger.error("Failed to retrieve indexed chunk_ids: %s", exc)
        raise RuntimeError(f"Failed to query indexed chunk_ids: {exc}") from exc
