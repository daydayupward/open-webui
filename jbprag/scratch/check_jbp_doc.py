import psycopg

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Query all sources in metadata
            cur.execute("SELECT DISTINCT cmetadata->>'source' FROM langchain_pg_embedding")
            sources = [r[0] for r in cur.fetchall()]
            print("=== Distinct Sources in Vector Store ===")
            for s in sources:
                print(f"Source: {s}")
            print()
            
            # Query documents in SQLite documents table
            # Let's check admin.db SQLite database
            import sqlite3
            db_path = "/home/eason/proj/open-webui/jbprag/data/admin.db"
            print(f"=== Inspecting SQLite Admin DB: {db_path} ===")
            if os.path.exists(db_path):
                sconn = sqlite3.connect(db_path)
                sconn.row_factory = sqlite3.Row
                scur = sconn.cursor()
                scur.execute("SELECT * FROM documents")
                docs = scur.fetchall()
                print(f"Total documents in admin.db: {len(docs)}")
                for d in docs:
                    print(f"Doc ID: {d['doc_id']}, Filename: {d['filename']}, Category: {d['category']}, Status: {d['status']}")
                sconn.close()
            else:
                print("SQLite Admin DB does not exist.")
                
except Exception as e:
    import os
    # Try importing os inside except to avoid name error if it failed before
    print(f"Error checking documents: {e}")
