from src.vector_store import get_vector_store
from src.utils import get_embeddings
from src.settings import settings
import numpy as np

def main():
    query = 'What is STA (Static Timing Analysis)?'
    connection_string = settings.DATABASE_URL
    embeddings = get_embeddings()
    vs = get_vector_store(connection_string, "eda_manuals", embeddings)
    
    # 1. Similarity search with score
    print("=== Raw Similarity Search ===")
    docs_and_scores = vs.similarity_search_with_relevance_scores(query, k=10)
    for idx, (doc, score) in enumerate(docs_and_scores, 1):
        print(f"[{idx}] Source: {doc.metadata.get('source')} Section: {doc.metadata.get('section')} Score: {score}")
        print(doc.page_content[:200])
        print("-" * 50)
        
if __name__ == '__main__':
    main()
