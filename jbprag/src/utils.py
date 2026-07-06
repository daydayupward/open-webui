from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from src.settings import settings
from functools import lru_cache

@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.0):
    return ChatOpenAI(
        base_url=settings.OPENAI_API_BASE_URL,
        api_key=settings.OPENAI_API_KEY,
        model=settings.LLM_MODEL,
        temperature=temperature
    )

@lru_cache(maxsize=4)
def get_visual_llm(temperature: float = 0.0):
    return ChatOpenAI(
        base_url=settings.VISUAL_API_BASE_URL or settings.OPENAI_API_BASE_URL,
        api_key=settings.VISUAL_API_KEY or settings.OPENAI_API_KEY,
        model=settings.VISUAL_MODEL or "gpt-image-2",
        temperature=temperature
    )

@lru_cache(maxsize=1)
def get_embeddings():
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_base=settings.OPENAI_API_BASE_URL,
        openai_api_key=settings.OPENAI_API_KEY
    )
