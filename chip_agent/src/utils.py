from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from src.settings import settings

def get_llm():
    return ChatOpenAI(
        base_url=settings.OPENAI_API_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        model=settings.LLM_MODEL,
        temperature=0.0
    )

def get_embeddings():
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_base=settings.OPENAI_API_BASE_URL,
        openai_api_key=settings.OPENAI_API_KEY
    )
