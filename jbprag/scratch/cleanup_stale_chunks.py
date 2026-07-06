import psycopg
import sys

db_url = 'postgresql://postgres:postgres@localhost:5432/chip_design'

def cleanup():
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Count before deletion
                cur.execute("""
                    SELECT COUNT(*) FROM langchain_pg_embedding 
                    WHERE cmetadata->>'source' = '/mnt/e/flow/03_JBP_PNR/jbp_pnr_ug.md'
                    AND cmetadata->>'updated_at' LIKE '2026-06-22%';
                """)
                count = cur.fetchone()[0]
                print(f"Stale chunks from 2026-06-22: {count}")
                
                if count > 0:
                    cur.execute("""
                        DELETE FROM langchain_pg_embedding 
                        WHERE cmetadata->>'source' = '/mnt/e/flow/03_JBP_PNR/jbp_pnr_ug.md'
                        AND cmetadata->>'updated_at' LIKE '2026-06-22%';
                    """)
                    print(f"Successfully deleted {count} stale chunks.")
                    conn.commit()
                else:
                    print("No stale chunks to delete.")
                    
    except Exception as e:
        print(f"Error during cleanup: {e}", file=sys.stderr)

if __name__ == '__main__':
    cleanup()
