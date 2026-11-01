from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol
from urllib.parse import urlparse, urlunparse

from app.config import Settings, get_settings
from app.utils.errors import ProviderError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    source: str | None
    published_at: datetime | None
    excerpt: str | None


class WebSearchProvider(Protocol):
    def search(
        self,
        query: str,
        limit: int = 5,
        search_kind: Literal["text", "news"] = "text",
        recency: Literal["day", "week", "month", "year"] = "week",
    ) -> list[WebSearchResult]: ...


def _clean_url(raw_url: object) -> str | None:
    if not isinstance(raw_url, str):
        return None
    parsed = urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def _parse_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


class DDGSWebSearchProvider:
    """Best-effort DuckDuckGo text/news metasearch adapter; no API key is required."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def search(
        self,
        query: str,
        limit: int = 5,
        search_kind: Literal["text", "news"] = "text",
        recency: Literal["day", "week", "month", "year"] = "week",
    ) -> list[WebSearchResult]:
        try:
            from ddgs import DDGS

            with DDGS(timeout=self._settings.web_search_timeout_seconds) as client:
                search = client.news if search_kind == "news" else client.text
                options = {"region": "us-en", "max_results": max(1, min(limit, 5)), "backend": "auto"}
                if search_kind == "news":
                    options["timelimit"] = {"day": "d", "week": "w", "month": "m", "year": "y"}[recency]
                rows = search(query=query[:500], **options)
        except ImportError as exc:
            raise ProviderError("DDGS web search is not installed. Install backend requirements.") from exc
        except Exception as exc:  # DDGS may surface network, timeout, or provider throttling errors.
            logger.info("DDGS request failed (%s)", type(exc).__name__)
            raise ProviderError("DuckDuckGo web search is unavailable or temporarily rate limited.") from exc

        if not isinstance(rows, list):
            raise ProviderError("DuckDuckGo returned malformed search results.")
        results: list[WebSearchResult] = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            url = _clean_url(row.get("url") or row.get("href"))
            if not title or not url:
                continue
            title_key = " ".join(title.casefold().split())
            if url in seen_urls or title_key in seen_titles:
                continue
            seen_urls.add(url)
            seen_titles.add(title_key)
            source = row.get("source")
            results.append(
                WebSearchResult(
                    title=title[:500],
                    url=url,
                    source=str(source).strip()[:120] if source else urlparse(url).hostname,
                    published_at=_parse_date(row.get("date")),
                    excerpt=str(row.get("body") or "").strip()[:700] or None,
                )
            )
        return results[: max(1, min(limit, 5))]
