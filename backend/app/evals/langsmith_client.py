from __future__ import annotations

import re
import sys
from typing import Any

from app.config import Settings


def create_langsmith_client(settings: Settings) -> Any:
    from langsmith import Client

    options: dict[str, Any] = {
        "api_key": settings.langsmith_api_key,
        "api_url": settings.langsmith_endpoint,
    }
    if settings.langsmith_workspace_id.strip():
        options["workspace_id"] = settings.langsmith_workspace_id.strip()
    return Client(**options)


def report_langsmith_error(exc: Exception, operation: str) -> int:
    message = str(exc).casefold()
    if "403" in message or "forbidden" in message:
        print(
            f"LangSmith denied {operation} (HTTP 403). Check that the API key can access this workspace "
            "and has dataset read/write permissions. For an organization-scoped service key, set "
            "LANGSMITH_WORKSPACE_ID in backend/.env. If the workspace is in the EU region, set "
            "LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com. The key itself was not printed.",
            file=sys.stderr,
        )
        return 3
    if "401" in message or "unauthorized" in message:
        print(
            f"LangSmith rejected the API key during {operation} (HTTP 401). In Settings > API Keys, "
            "the key list shows only a masked value; create a new Personal Access Token and copy the "
            "full secret from the one-time creation dialog into backend/.env. Also check that it is "
            "active, unexpired, and that LANGSMITH_ENDPOINT matches your workspace region. The key "
            "itself was not printed.",
            file=sys.stderr,
        )
        return 3
    detail = re.sub(r"lsv2_[A-Za-z0-9_-]+", "[redacted key]", str(exc)).replace("\n", " ")
    print(
        f"LangSmith {operation} failed ({type(exc).__name__}): {detail[:500]}",
        file=sys.stderr,
    )
    return 3
