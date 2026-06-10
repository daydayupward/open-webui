from langchain_postgres import PGVector
from langchain_core.embeddings import Embeddings

def get_vector_store(connection_string: str, collection_name: str, embeddings: Embeddings) -> PGVector:
    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True
    )

def query_vector_store(
    connection_string: str,
    collection_name: str,
    embeddings: Embeddings,
    query: str,
    k: int = 5,
    filter: dict = None
) -> list:
    try:
        store = get_vector_store(connection_string, collection_name, embeddings)
        return store.similarity_search(query, k=k, filter=filter)
    except Exception as e:
        raise RuntimeError(f"Vector store query failed: {e}")
