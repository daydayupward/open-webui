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
              AND c.cmetadata->>'section' LIKE '%Using the Mixed Placer%';
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} chunks from innovusUG.pdf matching section 'Using the Mixed Placer':")
        for idx, (doc, meta) in enumerate(rows, 1):
            print(f"[{idx}] Source: {meta.get('source')} | Section: {meta.get('section')}")
            print(f"Content: {doc}")
            print("-" * 50)

if __name__ == '__main__':
    main()
