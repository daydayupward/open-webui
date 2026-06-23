from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    OPENAI_API_BASE_URL: str = "http://jmaicloud.jaguarmicro.com:8100/v1"
    OPENAI_API_KEY: str = Field(..., description="OpenAI API Key")

    LLM_MODEL: str = "nvidia-nemotron-3-super-120b-a12b-fp8"
    EMBEDDING_MODEL: str = "bge-m3"
    RERANK_MODEL: str = "qwen3-reranker-8b"
    
    RERANK_API_BASE_URL: Optional[str] = None
    RERANK_API_KEY: Optional[str] = None
    
    VISUAL_API_BASE_URL: Optional[str] = "https://jmapi01.jaguarmicro.com"
    VISUAL_API_KEY: Optional[str] = None
    VISUAL_MODEL: str = "gpt-image-2"
    
    # Comma-separated categories to extract and describe images for
    IMAGE_INGESTION_CATEGORIES: str = "PDK,StdCell,SRAM,IP,Platform_Flow"
    
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/chip_design"

    @property
    def rerank_base_url(self) -> str:
        return self.RERANK_API_BASE_URL or self.OPENAI_API_BASE_URL

    @property
    def rerank_api_key(self) -> str:
        return self.RERANK_API_KEY or self.OPENAI_API_KEY

settings = Settings()
