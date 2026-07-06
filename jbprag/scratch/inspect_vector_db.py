import psycopg
import sys

db_url = 'postgresql://postgres:postgres@localhost:5432/chip_design'

def inspect_db():
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Query for specific image strings in documents
                # Query distinct doc_id statistics
                cur.execute("""
                    SELECT 
                        emb.cmetadata->>'doc_id' as doc_id,
                        MIN(emb.cmetadata->>'updated_at') as min_updated_at,
                        MAX(emb.cmetadata->>'updated_at') as max_updated_at,
                        COUNT(*) as chunk_count
                    FROM langchain_pg_embedding emb
                    WHERE emb.cmetadata->>'source' = '/mnt/e/flow/03_JBP_PNR/jbp_pnr_ug.md'
                    GROUP BY doc_id;
                """)
                rows = cur.fetchall()
                print("Doc ID stats for jbp_pnr_ug.md:")
                for r in rows:
                    print(f"Doc ID: {r[0]}")
                    print(f"  Min Updated At: {r[1]}")
                    print(f"  Max Updated At: {r[2]}")
                    print(f"  Chunk Count: {r[3]}")
                    print("-" * 40)
                    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

if __name__ == '__main__':
    inspect_db()

