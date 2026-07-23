import psycopg
import re

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cmetadata, document 
                FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%jbp_pnr_ug.md%' AND (document LIKE '%!\[%' OR document LIKE '%images%')
                LIMIT 5
            """)
            rows = cur.fetchall()
            print(f"=== Verification of jbp_pnr_ug.md images ===")
            print(f"Found {len(rows)} image-containing chunks")
            for i, row in enumerate(rows, 1):
                meta = row[0]
                doc = row[1]
                print(f"[{i}] Source: {meta.get('source')}")
                images = re.findall(r'!\[.*?\]\(.*?\)', doc)
                print(f"  Image tags: {images}")
                print("-" * 50)
                
except Exception as e:
    print(f"Error: {e}")
