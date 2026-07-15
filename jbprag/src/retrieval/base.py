from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from src.settings import settings
from src.utils import get_embeddings
from src.vector_store import query_vector_store
from src.retrieval.types import RetrievalChunk
from src.retrieval.reranker import QwenRerankerClient

def find_image_chunks(connection_string: str, collection_name: str, term: str) -> list:
    import psycopg
    conninfo = connection_string.replace("+psycopg", "")
    chunks = []
    try:
        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT e.document, e.cmetadata
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                    WHERE c.name = %s
                      AND e.document LIKE %s
                      AND (e.document ILIKE %s OR e.cmetadata->>'section' ILIKE %s);
                """, (collection_name, "%/static/uploads/images/%", f"%{term}%", f"%{term}%"))
                rows = cur.fetchall()
                for doc, meta in rows:
                    chunks.append((doc, meta))
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Failed to find image chunks: %s", e)
    return chunks

class BaseRetriever(ABC):
    _default_collection_name: str
    category_filter: str
    
    @property
    def collection_name(self) -> str:
        from src.admin_db import get_config
        config_key = f"{self._default_collection_name}_collection"
        try:
            return get_config().get(config_key, self._default_collection_name)
        except Exception:
            return self._default_collection_name
    
    def retrieve(self, query: str, metadata: Dict[str, Any], fetch_k: int = 50, top_k: int = 10) -> Dict[str, Any]:
        # Query Expansion for common abbreviations
        import re
        expanded_query = query
        abbrevs = {
            r'\bsta\b': 'STA (Static Timing Analysis)',
            r'\bdrc\b': 'DRC (Design Rule Check)',
            r'\blvs\b': 'LVS (Layout Versus Schematic)',
            r'\bpdk\b': 'PDK (Process Design Kit)',
            r'\beda\b': 'EDA (Electronic Design Automation)'
        }
        for pattern, replacement in abbrevs.items():
            if re.search(pattern, query, re.IGNORECASE):
                explanation = replacement.split('(')[1].rstrip(')').lower()
                if explanation not in query.lower():
                    expanded_query = re.sub(pattern, replacement, expanded_query, flags=re.IGNORECASE)

        db_filter = self._build_filter(metadata)
        
        # Extract source path filter if query mentions a specific manual
        query_lower = query.lower()
        if "innovusug" in query_lower or "innovus ug" in query_lower:
            db_filter["source"] = "/home/eason/proj/open-webui/ragdoc/innovus_cui/innovusUG.pdf"
        elif "innovustcr" in query_lower or "innovus tcr" in query_lower:
            db_filter["source"] = "/home/eason/proj/open-webui/ragdoc/innovus_cui/innovusTCR.pdf"
        elif "dbcom" in query_lower:
            db_filter["source"] = "/home/eason/proj/open-webui/ragdoc/innovus_cui/DBcom.pdf"
        elif "jbp_pnr_ug" in query_lower or "jbp pnr ug" in query_lower or "jbp-pnr-ug" in query_lower:
            db_filter["source"] = "/mnt/e/flow/03_JBP_PNR/jbp_pnr_ug.md"
        
        connection_string = settings.DATABASE_URL
        embeddings = get_embeddings()
        
        chunks = []
        logs = {
            "step": f"{self.category_filter} Retrieval",
            "filter": db_filter,
            "query": expanded_query,
            "original_query": query,
            "fetch_k": fetch_k,
            "top_k": top_k,
            "status": "success",
            "error": None,
            "retrieved_count": 0,
            "reranked_count": 0
        }
        
        try:
            docs = query_vector_store(
                connection_string=connection_string,
                collection_name=self.collection_name,
                embeddings=embeddings,
                query=expanded_query,
                k=fetch_k,
                filter=db_filter
            )
            
            raw_chunks = [
                RetrievalChunk(
                    page_content=doc.page_content,
                    metadata=doc.metadata
                )
                for doc in docs
            ]
            
            # Targeted image chunk retrieval if user query is asking for diagrams/images
            query_lower = query.lower()
            wants_image = any(kw in query_lower for kw in ["图", "图片", "流程图", "示意图", "结构图", "diagram", "flowchart", "image", "figure", "illustration"])
            extra_image_chunks = []
            if wants_image:
                import re
                terms = re.findall(r'[a-zA-Z]{3,}', query)
                STOP_WORDS = {"the", "and", "for", "with", "flow", "chart", "step", "steps", "diagram", "page", "file", "innovus", "icc2", "calibre", "primetime", "manual", "guide", "pdf", "tcr", "ug", "cui"}
                filtered_terms = [t for t in terms if t.lower() not in STOP_WORDS]
                
                chinese_terms = re.findall(r'[\u4e00-\u9fff]{2,}', query)
                CN_STOP_WORDS = {"流程", "步骤", "如何", "怎么", "什么", "使用", "怎样", "哪些", "它的", "有没有"}
                filtered_cn_terms = [t for t in chinese_terms if t not in CN_STOP_WORDS]
                
                all_terms = filtered_terms + filtered_cn_terms
                
                seen_docs = set(c.page_content for c in raw_chunks)
                for term in all_terms:
                    rows = find_image_chunks(connection_string, self.collection_name, term)
                    for doc, meta in rows:
                        # Apply source filter if present
                        if "source" in db_filter and meta.get("source") != db_filter["source"]:
                            continue
                        # Apply tool filter if present
                        if "tool" in db_filter and db_filter["tool"].get("$nin"):
                            tool_val = meta.get("tool")
                            if tool_val and tool_val in db_filter["tool"]["$nin"]:
                                continue
                                
                        if doc not in seen_docs:
                            seen_docs.add(doc)
                            extra_image_chunks.append(
                                RetrievalChunk(
                                    page_content=doc,
                                    metadata=meta
                                )
                            )
            raw_chunks = extra_image_chunks + raw_chunks
            for c in raw_chunks:
                parent_text = c.metadata.get("parent_text")
                if parent_text:
                    c.page_content = parent_text
            logs["retrieved_count"] = len(raw_chunks)
            
            reranker = QwenRerankerClient()
            ranked_chunks = reranker.rerank(query, raw_chunks, top_k=max(top_k, 15))
            
            # If the user query is asking for diagrams/images, boost chunks containing images
            query_lower = query.lower()
            wants_image = any(kw in query_lower for kw in ["图", "图片", "流程图", "示意图", "结构图", "diagram", "flowchart", "image", "figure", "illustration"])
            if wants_image:
                for c in ranked_chunks:
                    if "/static/uploads/images/" in c.page_content:
                        c.score = getattr(c, 'score', 0.0) + 10.0
                # Re-sort after boosting
                ranked_chunks.sort(key=lambda x: getattr(x, 'score', 0.0), reverse=True)
            
            chunks = ranked_chunks[:top_k]
            logs["reranked_count"] = len(chunks)
            
        except Exception as e:
            logs["status"] = "failed"
            logs["error"] = str(e)
            
        return {
            "chunks": chunks,
            "logs": logs
        }
        
    async def aretrieve(self, query: str, metadata: Dict[str, Any], fetch_k: int = 50, top_k: int = 10) -> Dict[str, Any]:
        # Query Expansion for common abbreviations
        import re
        expanded_query = query
        abbrevs = {
            r'\bsta\b': 'STA (Static Timing Analysis)',
            r'\bdrc\b': 'DRC (Design Rule Check)',
            r'\blvs\b': 'LVS (Layout Versus Schematic)',
            r'\bpdk\b': 'PDK (Process Design Kit)',
            r'\beda\b': 'EDA (Electronic Design Automation)'
        }
        for pattern, replacement in abbrevs.items():
            if re.search(pattern, query, re.IGNORECASE):
                explanation = replacement.split('(')[1].rstrip(')').lower()
                if explanation not in query.lower():
                    expanded_query = re.sub(pattern, replacement, expanded_query, flags=re.IGNORECASE)

        from src.vector_store import aquery_vector_store
        db_filter = self._build_filter(metadata)
        
        # Extract source path filter if query mentions a specific manual
        query_lower = query.lower()
        if "innovusug" in query_lower or "innovus ug" in query_lower:
            db_filter["source"] = "/home/eason/proj/open-webui/ragdoc/innovus_cui/innovusUG.pdf"
        elif "innovustcr" in query_lower or "innovus tcr" in query_lower:
            db_filter["source"] = "/home/eason/proj/open-webui/ragdoc/innovus_cui/innovusTCR.pdf"
        elif "dbcom" in query_lower:
            db_filter["source"] = "/home/eason/proj/open-webui/ragdoc/innovus_cui/DBcom.pdf"
        elif "jbp_pnr_ug" in query_lower or "jbp pnr ug" in query_lower or "jbp-pnr-ug" in query_lower:
            db_filter["source"] = "/mnt/e/flow/03_JBP_PNR/jbp_pnr_ug.md"
        
        connection_string = settings.DATABASE_URL
        embeddings = get_embeddings()
        
        chunks = []
        logs = {
            "step": f"{self.category_filter} Retrieval",
            "filter": db_filter,
            "query": expanded_query,
            "original_query": query,
            "fetch_k": fetch_k,
            "top_k": top_k,
            "status": "success",
            "error": None,
            "retrieved_count": 0,
            "reranked_count": 0
        }
        
        try:
            docs = await aquery_vector_store(
                connection_string=connection_string,
                collection_name=self.collection_name,
                embeddings=embeddings,
                query=expanded_query,
                k=fetch_k,
                filter=db_filter
            )
            
            raw_chunks = [
                RetrievalChunk(
                    page_content=doc.page_content,
                    metadata=doc.metadata
                )
                for doc in docs
            ]
            
            # Targeted image chunk retrieval if user query is asking for diagrams/images
            query_lower = query.lower()
            wants_image = any(kw in query_lower for kw in ["图", "图片", "流程图", "示意图", "结构图", "diagram", "flowchart", "image", "figure", "illustration"])
            extra_image_chunks = []
            if wants_image:
                import re
                terms = re.findall(r'[a-zA-Z]{3,}', query)
                STOP_WORDS = {"the", "and", "for", "with", "flow", "chart", "step", "steps", "diagram", "page", "file", "innovus", "icc2", "calibre", "primetime", "manual", "guide", "pdf", "tcr", "ug", "cui"}
                filtered_terms = [t for t in terms if t.lower() not in STOP_WORDS]
                
                chinese_terms = re.findall(r'[\u4e00-\u9fff]{2,}', query)
                CN_STOP_WORDS = {"流程", "步骤", "如何", "怎么", "什么", "使用", "怎样", "哪些", "它的", "有没有"}
                filtered_cn_terms = [t for t in chinese_terms if t not in CN_STOP_WORDS]
                
                all_terms = filtered_terms + filtered_cn_terms
                
                # Direct psycopg database query run in a thread pool for safety
                import asyncio
                loop = asyncio.get_event_loop()
                
                # Fetch image chunks for all terms
                all_rows = []
                for term in all_terms:
                    rows = await loop.run_in_executor(
                        None, 
                        find_image_chunks, 
                        connection_string, 
                        self.collection_name, 
                        term
                    )
                    all_rows.extend(rows)
                    
                seen_docs = set(c.page_content for c in raw_chunks)
                for doc, meta in all_rows:
                    # Apply source filter if present
                    if "source" in db_filter and meta.get("source") != db_filter["source"]:
                        continue
                    # Apply tool filter if present
                    if "tool" in db_filter and db_filter["tool"].get("$nin"):
                        tool_val = meta.get("tool")
                        if tool_val and tool_val in db_filter["tool"]["$nin"]:
                            continue
                            
                    if doc not in seen_docs:
                        seen_docs.add(doc)
                        extra_image_chunks.append(
                            RetrievalChunk(
                                page_content=doc,
                                metadata=meta
                            )
                        )
            raw_chunks = extra_image_chunks + raw_chunks
            for c in raw_chunks:
                parent_text = c.metadata.get("parent_text")
                if parent_text:
                    c.page_content = parent_text
            logs["retrieved_count"] = len(raw_chunks)
            
            reranker = QwenRerankerClient()
            ranked_chunks = reranker.rerank(query, raw_chunks, top_k=max(top_k, 15))
            
            # If the user query is asking for diagrams/images, boost chunks containing images
            query_lower = query.lower()
            wants_image = any(kw in query_lower for kw in ["图", "图片", "流程图", "示意图", "结构图", "diagram", "flowchart", "image", "figure", "illustration"])
            if wants_image:
                for c in ranked_chunks:
                    if "/static/uploads/images/" in c.page_content:
                        c.score = getattr(c, 'score', 0.0) + 10.0
                # Re-sort after boosting
                ranked_chunks.sort(key=lambda x: getattr(x, 'score', 0.0), reverse=True)
            
            chunks = ranked_chunks[:top_k]
            logs["reranked_count"] = len(chunks)
            
        except Exception as e:
            logs["status"] = "failed"
            logs["error"] = str(e)
            
        return {
            "chunks": chunks,
            "logs": logs
        }
        
    @abstractmethod
    def _build_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        pass
