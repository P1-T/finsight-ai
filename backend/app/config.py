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
    chat_requests_per_minute: int = 10
    company_search_requests_per_minute: int = 60
    trust_proxy_headers: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "finsight-evals"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_workspace_id: str = ""
    langsmith_eval_dataset: str = "FinSight Golden Evaluation v1"
    langsmith_eval_judge_model: str = "claude-haiku-4-5-20251001"


@lru_cache
def get_settings() -> Settings:
    return Settings()
