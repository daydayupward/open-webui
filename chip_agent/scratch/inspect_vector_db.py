import psycopg
import sys

db_url = 'postgresql://postgres:postgres@localhost:5432/chip_design'

def inspect_db():
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                print("Tables:", [r[0] for r in cur.fetchall()])
                
                cur.execute("SELECT name, uuid FROM langchain_pg_collection;")
                collections = cur.fetchall()
                print("Collections:")
                for col in collections:
                    col_name, col_uuid = col
                    print(f"  Name: {col_name}, UUID: {col_uuid}")
                    
                    cur.execute("SELECT COUNT(*) FROM langchain_pg_embedding WHERE collection_id = %s;", (col_uuid,))
                    cnt = cur.fetchone()[0]
                    print(f"    Total embedding rows: {cnt}")
                    
                    if cnt > 0:
                        cur.execute("SELECT document, cmetadata FROM langchain_pg_embedding WHERE collection_id = %s LIMIT 1;", (col_uuid,))
                        row = cur.fetchone()
                        if row:
                            doc, meta = row
                            print(f"    Sample Document: {doc[:100]}...")
                            print(f"    Sample Metadata: {meta}")
                        
                        # Get distinct categories in this collection
                        cur.execute("SELECT cmetadata->>'category' as cat, COUNT(*) FROM langchain_pg_embedding WHERE collection_id = %s GROUP BY cat;", (col_uuid,))
                        print("    Category distribution:")
                        for c_row in cur.fetchall():
                            print(f"      Category: {c_row[0]}, Count: {c_row[1]}")
                        
                        cur.execute("SELECT cmetadata->>'project_id' as proj, COUNT(*) FROM langchain_pg_embedding WHERE collection_id = %s GROUP BY proj;", (col_uuid,))
                        print("    Project ID distribution:")
                        for p_row in cur.fetchall():
                            print(f"      Project: {p_row[0]}, Count: {p_row[1]}")
                        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

if __name__ == '__main__':
    inspect_db()
