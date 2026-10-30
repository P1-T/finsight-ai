from datetime import datetime, timezone

import httpx

from app.api.schemas import Ticker
from app.config import Settings
from app.providers.news_provider import MarketNewsApiProvider
from app.utils.errors import ProviderError


def test_marketnews_request_and_normalization() -> None:
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "title": "Apple reports product update",
                        "url": "https://publisher.example/story/1",
                        "publisher": "Publisher Example",
                        "published_at": "2026-10-26T12:30:00Z",
                    },
                    {
                        "title": "Apple reports product update",
                        "url": "https://publisher.example/story/2",
                        "source": {"name": "Duplicate Source"},
                        "published_at": "2026-10-26T13:30:00+00:00",
                    },
                    {
                        "title": "Invalid link",
                        "url": "javascript:alert(1)",
                    },
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = MarketNewsApiProvider(Settings(marketnewsapi_key="private-test-key"), client=client)
    try:
        articles = provider.fetch(Ticker.AAPL, "Apple Inc.", max_records=15)
    finally:
        client.close()

    assert len(observed) == 1
    request = observed[0]
    assert request.url.path == "/v1/news"
    assert request.headers["Authorization"] == "Bearer private-test-key"
    assert request.url.params["tickers"] == "AAPL"
    assert request.url.params["category"] == "stocks"
    assert request.url.params["limit"] == "15"
    assert request.url.params["sort"] == "published_desc"
    assert len(articles) == 1
    assert articles[0].title == "Apple reports product update"
    assert articles[0].source == "Publisher Example"
    assert articles[0].url == "https://publisher.example/story/1"
    assert articles[0].published_at == datetime(2026, 10, 26, 12, 30, tzinfo=timezone.utc)


def test_marketnews_missing_key_is_clear_error() -> None:
    provider = MarketNewsApiProvider(Settings(marketnewsapi_key=""))
    try:
        provider.fetch(Ticker.AAPL, "Apple Inc.")
        raise AssertionError("expected missing-key error")
    except ProviderError as exc:
        assert "MARKETNEWSAPI_KEY" in str(exc)


def test_marketnews_rate_limit_is_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = MarketNewsApiProvider(Settings(marketnewsapi_key="test-key"), client=client)
    try:
        provider.fetch(Ticker.MSFT, "Microsoft Corporation")
        raise AssertionError("expected rate-limit error")
    except ProviderError as exc:
        assert "rate limit" in str(exc).lower()
    finally:
        client.close()


def test_marketnews_rejects_malformed_article_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"not": "a list"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = MarketNewsApiProvider(Settings(marketnewsapi_key="test-key"), client=client)
    try:
        provider.fetch(Ticker.NVDA, "NVIDIA Corporation")
        raise AssertionError("expected malformed-payload error")
    except ProviderError as exc:
        assert "unexpected article list" in str(exc)
    finally:
        client.close()
