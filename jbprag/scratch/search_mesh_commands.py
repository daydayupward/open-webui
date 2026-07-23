import psycopg

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cmetadata->>'source', cmetadata->>'section', count(*)
                FROM langchain_pg_embedding
                WHERE document LIKE '%ClockMesh%' OR document LIKE '%clockMesh%' OR document LIKE '%clock_mesh%'
                GROUP BY cmetadata->>'source', cmetadata->>'section'
            """)
            print("=== Chunks containing clock mesh commands ===")
            for row in cur.fetchall():
                print(f"Source: {row[0]} | Section: {row[1]} | Count: {row[2]}")
                
except Exception as e:
    print(f"Error: {e}")
