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
    llm_enabled: bool = True
    frontend_origin: str = "http://localhost:3000"
    sec_user_agent: str = "FinSightAI/2.0 your-email@example.com"
    sec_timeout_seconds: float = 30
    company_directory_cache_seconds: int = 86400
    web_search_timeout_seconds: float = 12
    market_data_timeout_seconds: float = 30
    llm_timeout_seconds: float = 60
    research_timeout_seconds: float = 90
    chat_history_messages: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
