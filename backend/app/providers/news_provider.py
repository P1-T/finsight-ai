from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import urlparse, urlunparse

import httpx

from app.api.schemas import Ticker
from app.config import Settings, get_settings
from app.utils.errors import ProviderError

ALLOWED_SCHEMES = {"http", "https"}


@dataclass(frozen=True)
class NormalizedArticle:
    title: str
    source: str | None
    published_at: datetime | None
    url: str


class NewsProvider(Protocol):
    def fetch(
        self,
        ticker: Ticker,
        company_name: str,
        max_records: int = 20,
    ) -> list[NormalizedArticle]: ...


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False
    if not parsed.netloc or " " in url:
        return False
    return True


def canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            parsed.query,
            "",
        )
    )


def parse_gdelt_datetime(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def normalize_articles(raw_articles: list[dict[str, object]]) -> list[NormalizedArticle]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    normalized: list[NormalizedArticle] = []

    for item in raw_articles:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or item.get("urlmobile") or "").strip()
        if not title or not is_valid_http_url(url):
            continue
        key = canonical_url(url)
        title_key = " ".join(title.lower().split())
        if key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(key)
        seen_titles.add(title_key)
        source = item.get("domain") or item.get("source")
        source_name = str(source).strip() if source else None
        published = parse_gdelt_datetime(item.get("seendate") or item.get("date"))
        normalized.append(
            NormalizedArticle(
                title=title,
                source=source_name or None,
                published_at=published,
                url=url,
            )
        )
    return normalized


def _parse_marketnews_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_marketnews_articles(raw_articles: list[dict[str, object]]) -> list[NormalizedArticle]:
    normalized: list[NormalizedArticle] = []
    for item in raw_articles:
        source = item.get("source")
        source_name: object = item.get("publisher")
        if isinstance(source, dict):
            source_name = source.get("name") or source.get("domain") or source_name
        elif isinstance(source, str):
            source_name = source_name or source
        normalized.append(
            NormalizedArticle(
                title=str(item.get("title") or "").strip(),
                source=str(source_name).strip() if source_name else None,
                published_at=_parse_marketnews_datetime(item.get("published_at")),
                url=str(item.get("url") or "").strip(),
            )
        )

    # Reuse the common URL validation and duplicate handling while retaining
    # MarketNewsAPI's ISO timestamp and publisher fields.
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result: list[NormalizedArticle] = []
    for article in normalized:
        if not article.title or not is_valid_http_url(article.url):
            continue
        url_key = canonical_url(article.url)
        title_key = " ".join(article.title.lower().split())
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        result.append(article)
    return result


class MarketNewsApiProvider:
    """Fetch recent company news from MarketNewsAPI's REST endpoint."""

    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client

    def fetch(self, ticker: Ticker, company_name: str, max_records: int = 20) -> list[NormalizedArticle]:
        del company_name  # The provider filters directly by the supported ticker.
        api_key = self._settings.marketnewsapi_key.strip()
        if not api_key:
            raise ProviderError("MarketNewsAPI key is not configured. Add MARKETNEWSAPI_KEY to backend/.env.")

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)
        params = {
            "tickers": ticker.value,
            "category": "stocks",
            "type": "news,press_release",
            "include_legal": "false",
            "from": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "to": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "sort": "published_desc",
            "limit": str(max(1, min(max_records, 100))),
        }
        url = f"{self._settings.marketnewsapi_base_url.rstrip('/')}/news"
        try:
            if self._client is not None:
                response = self._client.get(url, params=params, headers={"Authorization": f"Bearer {api_key}"})
            else:
                with httpx.Client(timeout=self._settings.gdelt_timeout_seconds) as client:
                    response = client.get(url, params=params, headers={"Authorization": f"Bearer {api_key}"})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise ProviderError("MarketNewsAPI rate limit reached. Try again later or check your plan quota.") from exc
            if status in {401, 403}:
                raise ProviderError("MarketNewsAPI rejected the configured API key or plan.") from exc
            raise ProviderError("News source (MarketNewsAPI) is unavailable or returned an error.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("News source (MarketNewsAPI) is unavailable or returned an error.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("News source (MarketNewsAPI) returned malformed data.") from exc
        if not isinstance(payload, dict):
            raise ProviderError("News source (MarketNewsAPI) returned an unexpected payload.")
        articles = payload.get("data")
        if not isinstance(articles, list):
            raise ProviderError("News source (MarketNewsAPI) returned an unexpected article list.")
        dict_articles = [item for item in articles if isinstance(item, dict)]
        return _normalize_marketnews_articles(dict_articles)[:max_records]


class GdeltNewsProvider:
    def __init__(self, settings: Settings | None = None, client: httpx.Client | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client

    def fetch(self, ticker: Ticker, company_name: str, max_records: int = 20) -> list[NormalizedArticle]:
        query = f'("{company_name}" OR {ticker.value}) sourcelang:english'
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": str(max_records),
            "timespan": "7d",
            "sort": "DateDesc",
        }
        try:
            if self._client is not None:
                response = self._client.get(self._settings.gdelt_doc_api, params=params)
            else:
                with httpx.Client(timeout=self._settings.gdelt_timeout_seconds) as client:
                    response = client.get(self._settings.gdelt_doc_api, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise ProviderError("News source (GDELT) is rate limited. Try again later.") from exc
            raise ProviderError("News source (GDELT) is unavailable or returned an error.") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("News source (GDELT) is unavailable or returned an error.") from exc

        content_type = response.headers.get("content-type", "")
        if "json" not in content_type.lower():
            text_prefix = response.text[:40].lstrip().lower()
            if text_prefix.startswith("<!doctype") or text_prefix.startswith("<html"):
                raise ProviderError("News source (GDELT) returned a non-JSON response.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("News source (GDELT) returned malformed data.") from exc

        if not isinstance(payload, dict):
            raise ProviderError("News source (GDELT) returned an unexpected payload.")

        articles = payload.get("articles")
        if articles is None:
            return []
        if not isinstance(articles, list):
            raise ProviderError("News source (GDELT) returned an unexpected article list.")

        dict_articles = [item for item in articles if isinstance(item, dict)]
        return normalize_articles(dict_articles)[:max_records]
