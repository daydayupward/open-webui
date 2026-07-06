import psycopg
import sys

db_url = 'postgresql://postgres:postgres@localhost:5432/chip_design'

def update_category():
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # First let's check how many rows match the source
                cur.execute(
                    "SELECT COUNT(*) FROM langchain_pg_embedding WHERE cmetadata->>'source' LIKE %s;",
                    ('%Static Timing Analysis%',)
                )
                count_before = cur.fetchone()[0]
                print(f"Found {count_before} chunks matching the book path.")
                
                if count_before > 0:
                    # Update category to Literature
                    cur.execute(
                        """
                        UPDATE langchain_pg_embedding 
                        SET cmetadata = jsonb_set(cmetadata, '{category}', '"Literature"')
                        WHERE cmetadata->>'source' LIKE %s;
                        """,
                        ('%Static Timing Analysis%',)
                    )
                    conn.commit()
                    print("Update committed.")
                    
                    # Verify
                    cur.execute(
                        "SELECT cmetadata->>'category' as cat, COUNT(*) FROM langchain_pg_embedding WHERE cmetadata->>'source' LIKE %s GROUP BY cat;",
                        ('%Static Timing Analysis%',)
                    )
                    for row in cur.fetchall():
                        print(f"After update - Category: {row[0]}, Count: {row[1]}")
                else:
                    print("No rows matched. Check book path.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

if __name__ == '__main__':
    update_category()
