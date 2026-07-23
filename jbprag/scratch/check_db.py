import psycopg

try:
    conn = psycopg.connect("postgresql://postgres:postgres@localhost:5432/jbpdoc")
    cur = conn.cursor()
    
    # Check collections
    cur.execute("SELECT uuid, name FROM langchain_pg_collection")
    collections = cur.fetchall()
    print("Collections:")
    for uuid, name in collections:
        cur.execute("SELECT count(*) FROM langchain_pg_embedding WHERE collection_id = %s", (uuid,))
        count = cur.fetchone()[0]
        print(f" - {name} (ID: {uuid}): {count} chunks")
        
    conn.close()
except Exception as e:
    print(f"Error checking database: {e}")
