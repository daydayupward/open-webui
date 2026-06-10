import os
from unittest.mock import patch
from src.settings import Settings

def test_settings_defaults():
    # Load settings with clear environment (or mock it)
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.OPENAI_API_BASE_URL == "http://jmaicloud.jaguarmicro.com:8100/v1"
        assert settings.LLM_MODEL == "nvidia-nemotron-3-super-120b-a12b-fp8"
        assert settings.EMBEDDING_MODEL == "bge-m3"
        assert settings.RERANK_MODEL == "qwen3-reranker-8b"
        assert settings.DATABASE_URL == "postgresql+psycopg://postgres:postgres@localhost:5432/chip_design"
        assert settings.rerank_base_url == "http://jmaicloud.jaguarmicro.com:8100/v1"
        assert settings.rerank_api_key == "gpustack_8a84577e7871ac6c_2c3d4ef8e376a5d2fca5ceb8e1cc4221"

def test_settings_override():
    test_env = {
        "OPENAI_API_BASE_URL": "http://test-base:8000/v1",
        "OPENAI_API_KEY": "test-key",
        "LLM_MODEL": "test-llm",
        "EMBEDDING_MODEL": "test-embedding",
        "RERANK_MODEL": "test-reranker",
        "RERANK_API_BASE_URL": "http://rerank-base:8000/v1",
        "RERANK_API_KEY": "rerank-key",
        "DATABASE_URL": "postgresql+psycopg://user:pass@localhost/db"
    }
    with patch.dict(os.environ, test_env, clear=True):
        settings = Settings()
        assert settings.OPENAI_API_BASE_URL == "http://test-base:8000/v1"
        assert settings.OPENAI_API_KEY == "test-key"
        assert settings.LLM_MODEL == "test-llm"
        assert settings.EMBEDDING_MODEL == "test-embedding"
        assert settings.RERANK_MODEL == "test-reranker"
        assert settings.rerank_base_url == "http://rerank-base:8000/v1"
        assert settings.rerank_api_key == "rerank-key"
        assert settings.DATABASE_URL == "postgresql+psycopg://user:pass@localhost/db"
