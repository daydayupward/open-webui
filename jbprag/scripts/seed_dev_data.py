#!/usr/bin/env python3
import sys
import os
import argparse
import json
import psycopg
from langchain_core.documents import Document
from src.settings import settings
from src.utils import get_embeddings
from src.vector_store import get_vector_store

def parse_args():
    parser = argparse.ArgumentParser(description="Seed local development database and vector store.")
    parser.add_argument("--vector-only", action="store_true", help="Seed vector database only")
    parser.add_argument("--metrics-only", action="store_true", help="Seed metrics database only")
    parser.add_argument("--reset", action="store_true", help="Reset (drop and recreate) tables/collections before seeding")
    return parser.parse_args()

def seed_metrics(reset=False):
    print("Seeding metrics database...")
    sql_file_path = os.path.join(os.path.dirname(__file__), "../dev_data/metrics_seed.sql")
    if not os.path.exists(sql_file_path):
        print(f"Error: SQL seed file not found at {sql_file_path}")
        return False
        
    try:
        conn_str = settings.DATABASE_URL
        if "postgresql+psycopg://" in conn_str:
            conn_str = conn_str.replace("postgresql+psycopg://", "postgresql://")
        elif "+psycopg" in conn_str:
            conn_str = conn_str.replace("+psycopg", "")
            
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                if reset:
                    print("Resetting metrics table...")
                    cur.execute("DROP TABLE IF EXISTS project_metrics;")
                    conn.commit()
                
                with open(sql_file_path, "r", encoding="utf-8") as f:
                    sql_script = f.read()
                
                cur.execute(sql_script)
                conn.commit()
                print("Metrics database seeded successfully.")
                return True
    except Exception as e:
        print(f"Warning: Could not seed metrics database: {e}")
        return False

def seed_vector_store(reset=False):
    print("Seeding vector store...")
    dev_data_dir = os.path.join(os.path.dirname(__file__), "../dev_data")
    
    files_and_cols = [
        ("pdk_rules.jsonl", "pdk_rules"),
        ("eda_manuals.jsonl", "eda_manuals"),
        ("project_docs.jsonl", "project_docs"),
    ]
    
    embeddings = get_embeddings()
    connection_string = settings.DATABASE_URL
    
    success = True
    for filename, collection_name in files_and_cols:
        file_path = os.path.join(dev_data_dir, filename)
        if not os.path.exists(file_path):
            print(f"Error: Seed file not found at {file_path}")
            success = False
            continue
            
        print(f"Seeding collection '{collection_name}' from {filename}...")
        
        try:
            if reset:
                conn_str = connection_string
                if "postgresql+psycopg://" in conn_str:
                    conn_str = conn_str.replace("postgresql+psycopg://", "postgresql://")
                with psycopg.connect(conn_str) as conn:
                    with conn.cursor() as cur:
                        # Check if table langchain_pg_collection exists first to avoid error if it does not
                        cur.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'langchain_pg_collection'
                            );
                        """)
                        if cur.fetchone()[0]:
                            cur.execute("""
                                DELETE FROM langchain_pg_embedding 
                                WHERE collection_id = (
                                    SELECT uuid FROM langchain_pg_collection WHERE name = %s
                                );
                            """, (collection_name,))
                            cur.execute("DELETE FROM langchain_pg_collection WHERE name = %s;", (collection_name,))
                            conn.commit()
                            print(f"Reset collection '{collection_name}' successfully.")
            
            vector_store = get_vector_store(
                connection_string=connection_string,
                collection_name=collection_name,
                embeddings=embeddings
            )
            
            documents = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    doc = Document(
                        page_content=item["text"],
                        metadata=item["metadata"]
                    )
                    documents.append(doc)
            
            if documents:
                vector_store.add_documents(documents)
                print(f"Seeded {len(documents)} documents into '{collection_name}'.")
            else:
                print(f"No documents found in {filename}.")
                
        except Exception as e:
            print(f"Warning: Could not seed collection '{collection_name}': {e}")
            success = False
            
    return success

def main():
    args = parse_args()
    run_all = not args.vector_only and not args.metrics_only
    
    vector_success = True
    metrics_success = True
    
    if run_all or args.vector_only:
        vector_success = seed_vector_store(reset=args.reset)
        
    if run_all or args.metrics_only:
        metrics_success = seed_metrics(reset=args.reset)
        
    if not vector_success or not metrics_success:
        print("Seeding finished with warnings (likely offline database).")
        sys.exit(0)
    else:
        print("All seeding completed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
