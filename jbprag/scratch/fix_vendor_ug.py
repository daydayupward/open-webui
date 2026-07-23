import psycopg
from src.settings import settings

def main():
    print("=== Fixing Vendor Metadata for innovusUG.pdf in Database ===")
    connection_string = settings.DATABASE_URL
    conninfo = connection_string.replace("+psycopg", "")
    
    try:
        with psycopg.connect(conninfo) as conn:
            with conn.cursor() as cur:
                # Run the update statement
                cur.execute("""
                    UPDATE langchain_pg_embedding
                    SET cmetadata = jsonb_set(cmetadata, '{vendor}', '"cadence"')
                    WHERE cmetadata->>'source' LIKE '%innovusUG.pdf';
                """)
                rowcount = cur.rowcount
                conn.commit()
                print(f"Successfully updated {rowcount} chunks.")
                
                # Check status again
                cur.execute("""
                    SELECT 
                        cmetadata->>'category' as cat, 
                        cmetadata->>'vendor' as vend,
                        cmetadata->>'source' as src,
                        COUNT(*) 
                    FROM langchain_pg_embedding 
                    WHERE cmetadata->>'source' LIKE '%innovusUG.pdf'
                    GROUP BY cat, vend, src;
                """)
                rows = cur.fetchall()
                print("\nUpdated metadata for innovusUG.pdf:")
                for cat, vend, src, cnt in rows:
                    src_name = src.split("/")[-1] if src else "None"
                    print(f"  * Category: {cat} | Vendor: {vend} | Source: {src_name} | Count: {cnt}")
                    
    except Exception as e:
        print(f"Error executing database update: {e}")

if __name__ == '__main__':
    main()
