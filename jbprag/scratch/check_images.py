import psycopg

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Check langchain_pg_embedding for markdown image syntax: ![*](*)
            # Specifically searching for "/static/uploads/images/" or "![" in document content
            cur.execute("""
                SELECT count(*) 
                FROM langchain_pg_embedding 
                WHERE document LIKE '%!\[%' OR document LIKE '%/static/uploads/images/%'
            """)
            count = cur.fetchone()[0]
            print(f"=== Image Chunks in PGVector ===")
            print(f"Total chunks containing image links or tags: {count}\n")
            
            if count > 0:
                cur.execute("""
                    SELECT collection_id, cmetadata, SUBSTRING(document FROM 1 FOR 300) 
                    FROM langchain_pg_embedding 
                    WHERE document LIKE '%!\[%' OR document LIKE '%/static/uploads/images/%'
                    LIMIT 10
                """)
                rows = cur.fetchall()
                print("=== Sample Image Chunks ===")
                for row in rows:
                    col_id = row[0]
                    meta = row[1]
                    snippet = row[2]
                    print(f"Collection ID: {col_id}")
                    print(f"Metadata: {meta}")
                    print(f"Text Snippet:\n{snippet}")
                    print("-" * 50)
            else:
                # Let's inspect the files in the static uploads folder to see if any images exist on disk
                import os
                static_dir = "/home/eason/proj/open-webui/backend/open_webui/static/uploads/images"
                print(f"=== Inspecting disk directory: {static_dir} ===")
                if os.path.exists(static_dir):
                    files = os.listdir(static_dir)
                    print(f"Total files on disk: {len(files)}")
                    for f in files[:10]:
                        print(f" - {f}")
                else:
                    print("Directory does not exist on disk.")

except Exception as e:
    print(f"Error checking images: {e}")
