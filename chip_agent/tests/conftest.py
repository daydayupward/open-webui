import pytest
import os
os.environ["OPENAI_API_KEY"] = "dummy_key_for_tests"

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(autouse=True)
def clear_caches():
    from src.utils import get_llm, get_embeddings
    get_llm.cache_clear()
    get_embeddings.cache_clear()

