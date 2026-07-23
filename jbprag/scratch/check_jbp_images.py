import psycopg

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Query chunks related to jbp_pnr_ug.md and containing images
            cur.execute("""
                SELECT cmetadata, document 
                FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%jbp_pnr_ug.md%' AND (document LIKE '%!\[%' OR document LIKE '%images%')
            """)
            rows = cur.fetchall()
            print(f"=== Chunks in jbp_pnr_ug.md containing images: {len(rows)} ===")
            for i, row in enumerate(rows, 1):
                meta = row[0]
                doc = row[1]
                print(f"[{i}] Metadata: {meta}")
                # Find image markdown syntax in doc
                import re
                images = re.findall(r'!\[.*?\]\(.*?\)', doc)
                print(f"Image tags found: {images}")
                print("-" * 50)
                
except Exception as e:
    print(f"Error checking JBP PNR images: {e}")
