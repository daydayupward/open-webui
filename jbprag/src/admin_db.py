import sqlite3
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "admin.db"

def get_db_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite tables for administration, tracking, and logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Config Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Insert default configs if not present
    defaults = {
        "pdk_rules_collection": "pdk_rules",
        "eda_manuals_collection": "eda_manuals",
        "project_docs_collection": "project_docs",
        "default_header_margin": "50",
        "default_footer_margin": "60",
        "default_watermark": ""
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO admin_config (key, value) VALUES (?, ?)", (k, v))
        
    # 2. Documents Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            filepath TEXT,
            filename TEXT,
            category TEXT,
            node TEXT,
            tool TEXT,
            project_id TEXT,
            vendor TEXT,
            status TEXT,
            error_message TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 3. Traces Table (for observability dashboard)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id TEXT PRIMARY KEY,
            query TEXT,
            rewritten_query TEXT,
            retrieved_chunks TEXT, -- JSON list
            answer TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 4. Evaluations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id TEXT PRIMARY KEY,
            metrics_json TEXT, -- JSON data
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Admin SQLite database initialized at %s", DB_PATH)

def get_config() -> Dict[str, str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM admin_config")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def update_config(configs: Dict[str, str]):
    conn = get_db_connection()
    cursor = conn.cursor()
    for k, v in configs.items():
        cursor.execute("INSERT OR REPLACE INTO admin_config (key, value) VALUES (?, ?)", (k, str(v)))
    conn.commit()
    conn.close()

def save_document(doc_data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO documents 
        (doc_id, filepath, filename, category, node, tool, project_id, vendor, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_data["doc_id"],
        doc_data.get("filepath"),
        doc_data.get("filename"),
        doc_data.get("category"),
        doc_data.get("node"),
        doc_data.get("tool"),
        doc_data.get("project_id"),
        doc_data.get("vendor"),
        doc_data.get("status", "pending"),
        doc_data.get("error_message")
    ))
    conn.commit()
    conn.close()

def get_documents() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents ORDER BY upload_time DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_document(doc_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
    conn.commit()
    conn.close()

def save_trace(trace_id: str, query: str, rewritten_query: str, chunks: List[Dict[str, Any]], answer: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO traces (id, query, rewritten_query, retrieved_chunks, answer)
        VALUES (?, ?, ?, ?, ?)
    """, (
        trace_id,
        query,
        rewritten_query,
        json.dumps(chunks),
        answer
    ))
    conn.commit()
    conn.close()

def get_traces(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traces ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        try:
            d["retrieved_chunks"] = json.loads(d["retrieved_chunks"])
        except Exception:
            d["retrieved_chunks"] = []
        res.append(d)
    return res

def save_evaluation(eval_id: str, metrics: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO evaluations (id, metrics_json)
        VALUES (?, ?)
    """, (eval_id, json.dumps(metrics)))
    conn.commit()
    conn.close()

def get_evaluations() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evaluations ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        try:
            d["metrics"] = json.loads(d["metrics_json"])
        except Exception:
            d["metrics"] = {}
        res.append(d)
    return res
