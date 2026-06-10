import pytest
from src.utils import get_llm, get_embeddings
from src.settings import settings

def test_imports():
    # Verify core imports from upgraded stack
    import langchain
    import langgraph
    import langchain_postgres
    import langchain_openai
    import pydantic
    import pydantic_settings
    
    assert langchain.__version__ is not None

def test_model_initialization():
    # Verify we can initialize LLM and Embeddings with settings
    llm = get_llm()
    embeddings = get_embeddings()
    
    assert llm.model_name == settings.LLM_MODEL
    assert embeddings.model == settings.EMBEDDING_MODEL
