from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    frontend_origin: str = "http://localhost:3000"
    gdelt_doc_api: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    marketnewsapi_key: str = ""
    marketnewsapi_base_url: str = "https://api.marketnewsapi.com/v1"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "finsight-filings"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_embed_model: str = "llama-text-embed-v2"
    sec_user_agent: str = "FinSightAI/1.0 your-email@example.com"
    sec_timeout_seconds: float = 30
    gdelt_timeout_seconds: float = 20
    market_data_timeout_seconds: float = 30
    llm_timeout_seconds: float = 60
    research_timeout_seconds: float = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
