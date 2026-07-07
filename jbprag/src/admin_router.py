import os
import shutil
import uuid
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from src.settings import settings
from src.utils import get_llm, get_embeddings
from src.supervisor import parse_json_safely
from src.ingestion.loader import IngestionDocument
from src.ingestion.chunker import chunk_document
from src.ingestion.indexer import index_chunks, delete_by_doc_id
from src.ingestion.metadata_mapper import _generate_doc_id
from scripts.clean_pdf import clean_pdf_file
from scripts.ingest_documents import clean_text_content, process_markdown_images

import src.admin_db as admin_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

DOC_DIR = Path(__file__).parent.parent / "data" / "documents"

def get_all_vector_collections() -> List[str]:
    try:
        from src.sql.sql_client import execute_read_query
        rows = execute_read_query("SELECT name FROM langchain_pg_collection")
        return [row["name"] for row in rows]
    except Exception as e:
        logger.warning("Failed to query collections table, returning defaults: %s", e)
        return ["pdk_rules", "eda_manuals", "project_docs"]

# 1. Config Endpoints
@router.get("/config")
async def get_config():
    return admin_db.get_config()

@router.post("/config")
async def update_config(configs: Dict[str, str]):
    admin_db.update_config(configs)
    return {"status": "success", "config": admin_db.get_config()}

# 2. Documents Catalog Endpoints
@router.get("/documents")
async def get_documents():
    return admin_db.get_documents()

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    doc = admin_db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 1. Delete from Vector Store
    try:
        category = doc.get("category")
        collection_mapping = {
            "PDK": "pdk_rules_collection",
            "StdCell": "pdk_rules_collection",
            "SRAM": "pdk_rules_collection",
            "EDA": "eda_manuals_collection",
            "IP": "project_docs_collection",
            "Platform_Flow": "project_docs_collection",
            "Project_Doc": "project_docs_collection",
            "Script": "project_docs_collection",
            "Literature": "project_docs_collection",
            "General": "project_docs_collection"
        }
        config_key = collection_mapping.get(category, "project_docs_collection")
        config = admin_db.get_config()
        collection_name = config.get(config_key, "project_docs")
        
        embeddings = get_embeddings()
        connection_string = settings.DATABASE_URL
        
        logger.info("Deleting doc_id=%s from collection=%s...", doc_id, collection_name)
        delete_by_doc_id(doc_id, connection_string, collection_name, embeddings)
    except Exception as e:
        logger.error("Failed to delete chunks from vector store: %s", e)
        
    # 2. Delete original file
    filepath = doc.get("filepath")
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            logger.warning("Failed to delete original file: %s", e)
            
    # 3. Delete from DB
    admin_db.delete_document(doc_id)
    return {"status": "success"}

@router.put("/documents/{doc_id}/metadata")
async def update_document_metadata(doc_id: str, payload: Dict[str, Any], background_tasks: BackgroundTasks):
    doc = admin_db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Get new metadata values
    category = payload.get("category", doc["category"])
    node = payload.get("node", doc["node"])
    tool = payload.get("tool", doc["tool"])
    project_id = payload.get("project_id", doc["project_id"])
    vendor = payload.get("vendor", doc["vendor"])
    
    # Update SQLite record first (status pending)
    updated_doc = dict(doc)
    updated_doc.update({
        "category": category,
        "node": node,
        "tool": tool,
        "project_id": project_id,
        "vendor": vendor,
        "status": "pending",
        "error_message": None
    })
    admin_db.save_document(updated_doc)
    
    # Re-ingest background task
    background_tasks.add_task(
        reingest_document_task,
        doc_id=doc_id,
        filepath=doc["filepath"],
        old_category=doc["category"],
        new_metadata={
            "category": category,
            "node": node,
            "tool": tool,
            "project_id": project_id,
            "vendor": vendor
        }
    )
    
    return {"status": "success", "message": "Re-ingestion triggered in background"}

# 3. Ingestion & Precheck
@router.post("/ingest/precheck")
async def ingest_precheck(file: UploadFile = File(...)):
    # 1. Read first page/bytes
    contents = await file.read()
    excerpt = ""
    if file.filename.lower().endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=contents, filetype="pdf")
            if len(doc) > 0:
                excerpt = doc[0].get_text()[:2000]
            doc.close()
        except Exception as e:
            logger.warning("Precheck PDF extract failed: %s", e)
            excerpt = contents[:2000].decode("utf-8", errors="ignore")
    else:
        excerpt = contents[:3000].decode("utf-8", errors="ignore")
        
    # 2. Call LLM to classify
    llm = get_llm(temperature=0.0)
    prompt = (
        "You are an assistant for chip design documentation management.\n"
        "Analyze the following document's filename and content excerpt. "
        "Infer its most likely Category and Vendor.\n\n"
        "Allowed categories: PDK, StdCell, SRAM, IP, EDA, Platform_Flow, Project_Doc, Script, Literature\n"
        "Allowed vendors: TSMC, Synopsys, Cadence, or null if none is mentioned.\n\n"
        f"Filename: {file.filename}\n"
        f"Excerpt:\n{excerpt}\n\n"
        "Output strictly a valid JSON object matching this schema:\n"
        '{"category": "string", "vendor": "string or null"}'
    )
    
    try:
        response = await llm.ainvoke(prompt)
        parsed = parse_json_safely(response.content)
        return parsed
    except Exception as e:
        logger.error("Precheck LLM classification failed: %s", e)
        return {"category": "PDK", "vendor": None}

@router.post("/ingest")
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form(...),
    node: Optional[str] = Form(None),
    tool: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    vendor: Optional[str] = Form(None),
    header_margin: Optional[int] = Form(None),
    footer_margin: Optional[int] = Form(None),
    watermark: Optional[str] = Form(None)
):
    # 1. Save file to permanent location
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())[:8]
    safe_filename = f"{file_id}_{file.filename}"
    filepath = DOC_DIR / safe_filename
    
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
        
    # 2. Calculate dummy doc_id
    doc_id = hashlib.sha256(f"{safe_filename}".encode("utf-8")).hexdigest()[:16]
    
    # 3. Save pending record to db
    doc_data = {
        "doc_id": doc_id,
        "filepath": str(filepath.absolute()),
        "filename": file.filename,
        "category": category,
        "node": node,
        "tool": tool,
        "project_id": project_id,
        "vendor": vendor,
        "status": "pending",
        "error_message": None
    }
    admin_db.save_document(doc_data)
    
    # 4. Trigger Ingest background task
    background_tasks.add_task(
        ingest_document_task,
        doc_id=doc_id,
        filepath=filepath,
        metadata={
            "category": category,
            "node": node,
            "tool": tool,
            "project_id": project_id,
            "vendor": vendor
        },
        cleaning={
            "header_margin": header_margin,
            "footer_margin": footer_margin,
            "watermark": watermark
        }
    )
    
    return {"status": "success", "doc_id": doc_id}

# 4. Indexing & Versioning
@router.get("/indexes")
async def get_indexes():
    collections = get_all_vector_collections()
    config = admin_db.get_config()
    return {
        "collections": collections,
        "active": {
            "PDK": config.get("pdk_rules_collection", "pdk_rules"),
            "EDA": config.get("eda_manuals_collection", "eda_manuals"),
            "Project": config.get("project_docs_collection", "project_docs")
        }
    }

@router.post("/indexes/switch")
async def switch_index(payload: Dict[str, str]):
    category = payload.get("category")  # "PDK" | "EDA" | "Project"
    target_collection = payload.get("collection")
    if not category or not target_collection:
        raise HTTPException(status_code=400, detail="Missing category or collection")
        
    config_keys = {
        "PDK": "pdk_rules_collection",
        "EDA": "eda_manuals_collection",
        "Project": "project_docs_collection"
    }
    key = config_keys.get(category)
    if not key:
         raise HTTPException(status_code=400, detail="Invalid category")
         
    admin_db.update_config({key: target_collection})
    return {"status": "success", "active": admin_db.get_config()}

@router.post("/indexes/test")
async def test_index(payload: Dict[str, Any]):
    query = payload.get("query")
    collection_name = payload.get("collection")
    k = payload.get("k", 5)
    if not query or not collection_name:
         raise HTTPException(status_code=400, detail="Missing query or collection")
         
    try:
        from src.vector_store import aquery_vector_store
        embeddings = get_embeddings()
        connection_string = settings.DATABASE_URL
        
        docs = await aquery_vector_store(
            connection_string=connection_string,
            collection_name=collection_name,
            embeddings=embeddings,
            query=query,
            k=k
        )
        
        # Get reranked results
        from src.retrieval.types import RetrievalChunk
        from src.retrieval.reranker import QwenRerankerClient
        
        raw_chunks = [
            RetrievalChunk(page_content=doc.page_content, metadata=doc.metadata)
            for doc in docs
        ]
        
        reranker = QwenRerankerClient()
        ranked = reranker.rerank(query, raw_chunks, top_k=k)
        
        res = []
        for c in ranked:
            res.append({
                "page_content": c.page_content,
                "metadata": c.metadata,
                "score": float(c.metadata.get("relevance_score", 0.0))
            })
        return {"chunks": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. Observability Traces & Evaluation
@router.get("/traces")
async def get_traces(limit: int = 50):
    return admin_db.get_traces(limit=limit)

@router.get("/evaluation")
async def get_evaluation():
    return admin_db.get_evaluations()


# ---------------------------------------------------------------------------
# Background Task Implementations
# ---------------------------------------------------------------------------

async def ingest_document_task(doc_id: str, filepath: Path, metadata: Dict[str, Any], cleaning: Dict[str, Any]):
    logger.info("Ingestion task started for %s", filepath.name)
    temp_pdf_path = None
    try:
        from markitdown import MarkItDown
        
        # Apply margins / watermarks from default config if not overridden
        config = admin_db.get_config()
        header_margin = cleaning.get("header_margin")
        if header_margin is None:
            header_margin = int(config.get("default_header_margin", 50))
            
        footer_margin = cleaning.get("footer_margin")
        if footer_margin is None:
            footer_margin = int(config.get("default_footer_margin", 60))
            
        watermark = cleaning.get("watermark")
        if watermark is None:
            watermark = config.get("default_watermark")
            if not watermark:
                watermark = None

        target_path = filepath
        # Physical Cleaning
        if filepath.suffix.lower() == ".pdf":
            import tempfile
            import os
            temp_fd, temp_pdf_str = tempfile.mkstemp(suffix=".pdf", prefix="temp_clean_")
            os.close(temp_fd)
            temp_pdf_path = Path(temp_pdf_str)
            
            cleaned = clean_pdf_file(
                input_path=filepath,
                output_path=temp_pdf_path,
                header_margin=header_margin,
                footer_margin=footer_margin,
                watermark=watermark
            )
            if cleaned:
                target_path = temp_pdf_path
            else:
                logger.warning("PDF physical cleaning failed, fallback to original")
                temp_pdf_path = None

        # Conversion
        suffix = filepath.suffix.lower()
        if suffix in (".md", ".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            if suffix == ".md":
                text = process_markdown_images(text, filepath.parent, metadata["category"])
        elif suffix == ".pdf":
            try:
                import pymupdf4llm
                logger.info("Converting PDF document via PyMuPDF4LLM: %s", target_path.name)
                text = pymupdf4llm.to_markdown(str(target_path.absolute()))
            except ImportError:
                logger.warning("pymupdf4llm is not installed, falling back to MarkItDown")
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(str(target_path.absolute()))
                text = result.text_content
        elif suffix in (".docx", ".xlsx", ".xls", ".pptx", ".html"):
            from markitdown import MarkItDown
            md = MarkItDown()
            logger.info("Converting Office/HTML document via MarkItDown: %s", target_path.name)
            result = md.convert(str(target_path.absolute()))
            text = result.text_content
        else:
            logger.warning("Unsupported file format %s. Trying MarkItDown fallback.", suffix)
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(str(target_path.absolute()))
            text = result.text_content

        # Watermark/Text clean
        text = clean_text_content(text, watermark)

        if not text or not text.strip():
             raise ValueError("Extracted text content is empty")

        doc = IngestionDocument(
            text=text,
            metadata=metadata,
            source=str(filepath.absolute())
        )
        
        # Chunker
        chunks = chunk_document(doc)
        
        # Indexer
        embeddings = get_embeddings()
        connection_string = settings.DATABASE_URL
        
        collection_mapping = {
            "PDK": "pdk_rules_collection",
            "StdCell": "pdk_rules_collection",
            "SRAM": "pdk_rules_collection",
            "EDA": "eda_manuals_collection",
            "IP": "project_docs_collection",
            "Platform_Flow": "project_docs_collection",
            "Project_Doc": "project_docs_collection",
            "Script": "project_docs_collection",
            "Literature": "project_docs_collection",
            "General": "project_docs_collection"
        }
        config_key = collection_mapping.get(metadata["category"], "project_docs_collection")
        collection_name = config.get(config_key, "project_docs")
        
        logger.info("Indexing doc_id=%s with %d chunks to collection=%s...", doc_id, len(chunks), collection_name)
        stats = index_chunks(
            chunks=chunks,
            connection_string=connection_string,
            collection_name=collection_name,
            embeddings=embeddings
        )
        
        # Update SQLite document record
        doc_record = admin_db.get_document(doc_id)
        if doc_record:
            doc_record["status"] = "success"
            doc_record["error_message"] = None
            admin_db.save_document(doc_record)
            logger.info("Ingestion successfully completed for doc_id=%s. Stats: %s", doc_id, stats)
            
    except Exception as e:
        logger.error("Ingestion task failed: %s", e, exc_info=True)
        doc_record = admin_db.get_document(doc_id)
        if doc_record:
            doc_record["status"] = "failed"
            doc_record["error_message"] = str(e)
            admin_db.save_document(doc_record)
    finally:
        if temp_pdf_path and temp_pdf_path.exists():
            try:
                os.remove(temp_pdf_path)
            except Exception:
                pass

async def reingest_document_task(doc_id: str, filepath: str, old_category: str, new_metadata: Dict[str, Any]):
    logger.info("Re-ingestion triggered for doc_id=%s (moving metadata)", doc_id)
    try:
        # 1. Delete old chunks from old collection name
        collection_mapping = {
            "PDK": "pdk_rules_collection",
            "StdCell": "pdk_rules_collection",
            "SRAM": "pdk_rules_collection",
            "EDA": "eda_manuals_collection",
            "IP": "project_docs_collection",
            "Platform_Flow": "project_docs_collection",
            "Project_Doc": "project_docs_collection",
            "Script": "project_docs_collection",
            "Literature": "project_docs_collection",
            "General": "project_docs_collection"
        }
        
        config = admin_db.get_config()
        old_config_key = collection_mapping.get(old_category, "project_docs_collection")
        old_collection_name = config.get(old_config_key, "project_docs")
        
        embeddings = get_embeddings()
        connection_string = settings.DATABASE_URL
        
        logger.info("Removing old chunks from collection=%s...", old_collection_name)
        delete_by_doc_id(doc_id, connection_string, old_collection_name, embeddings)
        
        # 2. Ingest document again with new metadata
        await ingest_document_task(
            doc_id=doc_id,
            filepath=Path(filepath),
            metadata=new_metadata,
            cleaning={} # Use default config values
        )
    except Exception as e:
        logger.error("Re-ingestion failed: %s", e, exc_info=True)
        doc_record = admin_db.get_document(doc_id)
        if doc_record:
            doc_record["status"] = "failed"
            doc_record["error_message"] = str(e)
            admin_db.save_document(doc_record)
