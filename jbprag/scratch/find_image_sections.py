import psycopg

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT document, cmetadata->>'page', cmetadata->>'section'
                FROM langchain_pg_embedding
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%'
                  AND document LIKE '%!\[%'
                LIMIT 10
            """)
            print("=== Sample chunks with images ===")
            for row in cur.fetchall():
                doc = row[0]
                page = row[1]
                sect = row[2]
                print(f"Page: {page} | Section: {sect}")
                # Find the image tag
                import re
                tags = re.findall(r'!\[.*?\]\(.*?\)', doc)
                print(f"Image tags found: {tags}")
                print(f"Snippet: {doc[:300]}")
                print("-" * 50)
                
except Exception as e:
    print(f"Error: {e}")
