import psycopg
import json

db_url = 'postgresql://postgres:postgres@localhost:5432/jbpdoc'

files_to_update = [
    '/home/eason/proj/open-webui/ragdoc/innovus_cui/innovusTCR.pdf',
    '/home/eason/proj/open-webui/ragdoc/innovus_cui/innovusUG.pdf',
    '/home/eason/proj/open-webui/ragdoc/innovus_cui/DBcom.pdf'
]

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            print("Starting update of vendor metadata...")
            
            total_updated = 0
            for file_path in files_to_update:
                # In PostgreSQL, cmetadata is a JSONB column.
                # We can check if cmetadata->>'source' matches the file_path,
                # and then update cmetadata by merging or setting the 'vendor' key.
                
                # Check how many chunks match first
                cur.execute(
                    "SELECT count(*) FROM langchain_pg_embedding WHERE cmetadata->>'source' = %s",
                    (file_path,)
                )
                countBefore = cur.fetchone()[0]
                print(f"File '{file_path}': Found {countBefore} chunks matching.")
                
                if countBefore > 0:
                    # Update cmetadata by setting 'vendor' to 'cadence'
                    cur.execute(
                        """
                        UPDATE langchain_pg_embedding 
                        SET cmetadata = jsonb_set(cmetadata, '{vendor}', '"cadence"', true)
                        WHERE cmetadata->>'source' = %s
                        """,
                        (file_path,)
                    )
                    conn.commit()
                    
                    cur.execute(
                        "SELECT count(*) FROM langchain_pg_embedding WHERE cmetadata->>'source' = %s AND cmetadata->>'vendor' = 'cadence'",
                        (file_path,)
                    )
                    countAfter = cur.fetchone()[0]
                    print(f"  -> Successfully updated. Chunks with vendor='cadence': {countAfter}")
                    total_updated += countAfter
                    
            print(f"\nUpdate complete! Total chunks updated: {total_updated}")
            
except Exception as e:
    print(f"Error during metadata update: {e}")
