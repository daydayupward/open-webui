import psycopg
from src.settings import settings

def main():
    conninfo = settings.DATABASE_URL.replace("+psycopg", "")
    conn = psycopg.connect(conninfo)
    with conn.cursor() as cur:
        # Search in project_docs collection
        cur.execute("""
            SELECT c.document, c.cmetadata
            FROM langchain_pg_embedding c
            JOIN langchain_pg_collection col ON c.collection_id = col.uuid
            WHERE col.name = 'project_docs'
              AND c.cmetadata->>'source' LIKE '%jbp_pnr_ug.md'
              AND c.document LIKE '%/static/uploads/images/%';
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} chunks from jbp_pnr_ug.md containing static image paths in the database:")
        for idx, (doc, meta) in enumerate(rows[:5], 1):
            print(f"[{idx}] Section: {meta.get('section')}")
            print(f"Content snippet: {doc[:300]}")
            print("-" * 50)

if __name__ == '__main__':
    main()
