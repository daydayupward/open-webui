import psycopg
import json

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Print tables
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            tables = [r[0] for r in cur.fetchall()]
            print("=== Public Tables ===")
            print(tables)
            print()
            
            # 2. Check collections if table exists
            if 'langchain_pg_collection' in tables:
                cur.execute("SELECT uuid, name, cmetadata FROM langchain_pg_collection")
                collections = cur.fetchall()
                print("=== Collections ===")
                for col in collections:
                    print(f"Collection UUID: {col[0]}, Name: {col[1]}, Metadata: {col[2]}")
                print()
                
                # For each collection, count embeddings
                if 'langchain_pg_embedding' in tables:
                    print("=== Embeddings Count by Collection ===")
                    for col in collections:
                        cur.execute("SELECT count(*) FROM langchain_pg_embedding WHERE collection_id = %s", (col[0],))
                        count = cur.fetchone()[0]
                        print(f"Collection '{col[1]}': {count} chunks")
                    print()
            
            # 3. List documents in the vector database
            # Let's inspect langchain_pg_embedding metadata
            if 'langchain_pg_embedding' in tables:
                print("=== Distinct Documents & Metadata ===")
                # Query all cmetadata columns
                cur.execute("SELECT cmetadata FROM langchain_pg_embedding")
                rows = cur.fetchall()
                
                docs = {}
                for row in rows:
                    meta = row[0]
                    if not meta:
                        continue
                    # Clean metadata is dict
                    # Try to extract doc identifier
                    source = meta.get('source', 'Unknown')
                    category = meta.get('category', 'Unknown')
                    project_id = meta.get('project_id', 'None')
                    vendor = meta.get('vendor', 'None')
                    
                    key = (source, category, project_id, vendor)
                    docs[key] = docs.get(key, 0) + 1
                
                for (source, category, proj, vend), count in docs.items():
                    print(f"Document: {source}")
                    print(f"  Category: {category}")
                    print(f"  Project ID: {proj}")
                    print(f"  Vendor: {vend}")
                    print(f"  Chunks: {count}")
                    print("-" * 40)
except Exception as e:
    print(f"Error querying database: {e}")
