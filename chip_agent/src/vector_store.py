from langchain_postgres import PGVector
from langchain_core.embeddings import Embeddings

def get_vector_store(connection_string: str, collection_name: str, embeddings: Embeddings) -> PGVector:
    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True
    )
