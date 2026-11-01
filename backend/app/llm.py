from __future__ import annotations

from app.config import Settings, get_settings
from app.utils.errors import AgentError


def require_api_key(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    key = (resolved.anthropic_api_key or "").strip()
    if not key:
        raise AgentError("Anthropic API key is not configured on the server.")
    return key


def get_chat_model(settings: Settings | None = None, *, max_tokens: int | None = None):
    resolved = settings or get_settings()
    api_key = require_api_key(resolved)
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=resolved.anthropic_model,
        api_key=api_key,
        timeout=resolved.llm_timeout_seconds,
        max_retries=1,
        max_tokens_to_sample=max_tokens,
    )
