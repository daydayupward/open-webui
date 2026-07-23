import psycopg

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Search for chunks containing mesh or clock and see if they have images
            cur.execute("""
                SELECT document, cmetadata->>'page', cmetadata->>'section'
                FROM langchain_pg_embedding
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%'
                  AND (document LIKE '%mesh%' OR document LIKE '%Mesh%')
                LIMIT 10
            """)
            print("=== Chunks containing 'mesh' ===")
            for row in cur.fetchall():
                doc = row[0]
                page = row[1]
                sect = row[2]
                has_image = "![" in doc
                print(f"Page: {page} | Section: {sect} | Has Image: {has_image}")
                print(f"Snippet: {doc[:300]}")
                print("-" * 50)
                
except Exception as e:
    print(f"Error: {e}")
