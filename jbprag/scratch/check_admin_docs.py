import sqlite3
import os

db_path = "/home/eason/proj/open-webui/jbprag/data/admin.db"
print(f"=== Inspecting SQLite Admin DB: {db_path} ===")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM documents")
    docs = cur.fetchall()
    print(f"Total documents in admin.db: {len(docs)}")
    for d in docs:
        print(f"Doc ID: {d['doc_id']}")
        print(f"  Filename: {d['filename']}")
        print(f"  Filepath: {d['filepath']}")
        print(f"  Category: {d['category']}")
        print(f"  Status: {d['status']}")
        print(f"  Error: {d['error_message']}")
        print("-" * 30)
    conn.close()
else:
    print("SQLite Admin DB does not exist.")
