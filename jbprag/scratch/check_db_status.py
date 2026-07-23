import psycopg
from src.settings import settings

def main():
    print("=== Checking Vector Database Status ===")
    connection_string = settings.DATABASE_URL
    conninfo = connection_string.replace("+psycopg", "")
    
    try:
        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cur:
                # 1. Get collection list
                cur.execute("SELECT uuid, name FROM langchain_pg_collection;")
                collections = cur.fetchall()
                print(f"\nCollections found: {len(collections)}")
                for uuid, name in collections:
                    cur.execute("SELECT COUNT(*) FROM langchain_pg_embedding WHERE collection_id = %s;", (uuid,))
                    count = cur.fetchone()[0]
                    print(f" - Collection Name: '{name}' | Total Chunks: {count}")
                    
                    # 2. Check metadata categories and vendor for this collection
                    cur.execute("""
                        SELECT 
                            cmetadata->>'category' as cat, 
                            cmetadata->>'vendor' as vend,
                            cmetadata->>'source' as src,
                            COUNT(*) 
                        FROM langchain_pg_embedding 
                        WHERE collection_id = %s
                        GROUP BY cat, vend, src
                        ORDER BY COUNT(*) DESC
                        LIMIT 10;
                    """, (uuid,))
                    metadata_groups = cur.fetchall()
                    print("   Top Metadata Profiles:")
                    for cat, vend, src, cnt in metadata_groups:
                        src_name = src.split("/")[-1] if src else "None"
                        print(f"    * Category: {cat} | Vendor: {vend} | Source: {src_name} | Count: {cnt}")
                        
    except Exception as e:
        print(f"Error checking database status: {e}")

if __name__ == '__main__':
    main()
