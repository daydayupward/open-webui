import psycopg

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Query distinct doc_id and their counts/tmp status
            cur.execute("""
                SELECT cmetadata->>'doc_id', count(*), 
                       sum(case when document like '%/tmp/%' then 1 else 0 end) as tmp_count
                FROM langchain_pg_embedding 
                WHERE cmetadata->>'source' LIKE '%innovusUG.pdf%'
                GROUP BY cmetadata->>'doc_id'
            """)
            rows = cur.fetchall()
            print("=== doc_id breakdown for innovusUG.pdf ===")
            for row in rows:
                doc_id = row[0]
                total = row[1]
                tmp = row[2]
                print(f"Doc ID: {doc_id} | Total Chunks: {total} | Chunks with /tmp/: {tmp}")
            
            # 2. Delete doc_ids that contain /tmp/ paths
            for row in rows:
                doc_id = row[0]
                tmp = row[2]
                if tmp > 0:
                    print(f"Deleting old doc_id={doc_id} with broken /tmp/ paths...")
                    cur.execute("""
                        DELETE FROM langchain_pg_embedding 
                        WHERE cmetadata->>'doc_id' = %s
                    """, (doc_id,))
                    print(f"Successfully deleted doc_id={doc_id}")
            
            conn.commit()
            print("\nDatabase committed successfully!")
            
except Exception as e:
    print(f"Error: {e}")
