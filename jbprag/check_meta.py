from src.sql.sql_client import execute_read_query
rows = execute_read_query(
    "SELECT c.name, e.cmetadata, left(e.document, 80) as doc_preview FROM langchain_pg_collection c JOIN langchain_pg_embedding e ON e.collection_id = c.uuid WHERE c.name = 'eda_manuals' LIMIT 2"
)
for r in rows:
    print(r)
