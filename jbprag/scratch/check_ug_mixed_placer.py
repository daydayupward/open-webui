import psycopg
from src.settings import settings

def main():
    conninfo = settings.DATABASE_URL.replace("+psycopg", "")
    conn = psycopg.connect(conninfo)
    with conn.cursor() as cur:
        # Search in eda_manuals collection
        cur.execute("""
            SELECT c.document, c.cmetadata
            FROM langchain_pg_embedding c
            JOIN langchain_pg_collection col ON c.collection_id = col.uuid
            WHERE col.name = 'eda_manuals'
              AND c.cmetadata->>'source' LIKE '%innovusUG.pdf'
              AND (c.document LIKE '%mixed placer%' OR c.document LIKE '%mixed placement%');
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} chunks from innovusUG.pdf containing 'mixed placer/placement':")
        for idx, (doc, meta) in enumerate(rows, 1):
            print(f"[{idx}] Section: {meta.get('section')}")
            print(f"Snippet: {doc[:300]}")
            print("-" * 50)

if __name__ == '__main__':
    main()
