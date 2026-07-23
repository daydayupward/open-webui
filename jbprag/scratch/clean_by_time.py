import psycopg

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Check distinct updated_at timestamps
            cur.execute("""
                SELECT DISTINCT SUBSTRING(cmetadata->>'updated_at' FROM 1 FOR 10), count(*)
                FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%'
                GROUP BY DISTINCT SUBSTRING(cmetadata->>'updated_at' FROM 1 FOR 10)
            """)
            print("=== Timestamps breakdown ===")
            for row in cur.fetchall():
                print(f"Date: {row[0]} | Count: {row[1]}")
            print()
            
            # Delete old chunks where updated_at is NOT today (2026-07-08)
            print("Deleting old chunks from 2026-07-07...")
            cur.execute("""
                DELETE FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%' 
                  AND cmetadata->>'updated_at' LIKE '2026-07-07%'
            """)
            deleted = cur.rowcount
            print(f"Successfully deleted {deleted} old chunks!")
            
            conn.commit()
            print("Database committed successfully!")
            
except Exception as e:
    print(f"Error: {e}")
