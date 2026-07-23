import psycopg
import re

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Total chunks for innovusUG.pdf
            cur.execute("""
                SELECT count(*) 
                FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%'
            """)
            total_chunks = cur.fetchone()[0]
            print(f"Total chunks for innovusUG.pdf: {total_chunks}")
            
            # 2. Total chunks containing any image syntax (e.g. ![] )
            cur.execute("""
                SELECT count(*) 
                FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%' AND document LIKE '%!\[%'
            """)
            img_chunks = cur.fetchone()[0]
            print(f"Chunks containing image syntax (![): {img_chunks}")
            
            # 3. Total chunks containing /static/uploads/images/ paths
            cur.execute("""
                SELECT count(*) 
                FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%' AND document LIKE '%/static/uploads/images/%'
            """)
            static_img_chunks = cur.fetchone()[0]
            print(f"Chunks containing static web image paths (/static/uploads/images/): {static_img_chunks}")
            
            # 4. Total chunks containing /tmp/ paths
            cur.execute("""
                SELECT count(*) 
                FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%' AND document LIKE '%/tmp/%'
            """)
            tmp_img_chunks = cur.fetchone()[0]
            print(f"Chunks containing temporary image paths (/tmp/): {tmp_img_chunks}")
            
            # 5. Let's see some sample image tags from innovusUG.pdf
            if img_chunks > 0:
                cur.execute("""
                    SELECT document 
                    FROM langchain_pg_embedding 
                    WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%' AND document LIKE '%!\[%'
                    LIMIT 3
                """)
                rows = cur.fetchall()
                print("\n=== Sample Image tags in innovusUG.pdf ===")
                for i, row in enumerate(rows, 1):
                    doc = row[0]
                    images = re.findall(r'!\[.*?\]\(.*?\)', doc)
                    print(f"Sample {i} image tags: {images}")
                    
except Exception as e:
    print(f"Error: {e}")
