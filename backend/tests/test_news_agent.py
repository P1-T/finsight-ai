from datetime import datetime, timezone

import httpx

from app.agents.news_agent import NewsLlmOutput, analyze_news
from app.api.schemas import NewsAnalysis, Ticker
from app.providers.news_provider import (
    GdeltNewsProvider,
    canonical_url,
    is_valid_http_url,
    normalize_articles,
)


class FakeStructured:
    def __init__(self, payload: NewsLlmOutput) -> None:
        self.payload = payload

    def invoke(self, _messages: object) -> NewsLlmOutput:
        return self.payload


class FakeLLM:
    def __init__(self, payload: NewsLlmOutput) -> None:
        self.payload = payload

    def with_structured_output(self, _schema: object, method: str = "json_schema") -> FakeStructured:
        assert method == "json_schema"
        return FakeStructured(self.payload)


def test_invalid_urls_rejected() -> None:
    assert is_valid_http_url("https://example.com/a")
    assert not is_valid_http_url("javascript:alert(1)")
    assert not is_valid_http_url("not-a-url")
    assert not is_valid_http_url("ftp://example.com/file")


def test_news_article_schema_preserves_original_url() -> None:
    from app.api.schemas import NewsArticle

    original = "https://Example.com/news?id=4&utm_source=gdelt"
    assert str(NewsArticle(title="Headline", url=original).url) == original
    try:
        NewsArticle(title="Bad", url="javascript:alert(1)")
        raise AssertionError("expected URL validation failure")
    except ValueError:
        pass


def test_article_normalization_and_dedupe() -> None:
    articles = normalize_articles(
        [
            {
                "title": "Apple earnings",
                "url": "https://Example.com/news/a/",
                "domain": "example.com",
                "seendate": "20240115T120000Z",
            },
            {
                "title": "Apple earnings",
                "url": "https://example.com/news/a",
                "domain": "example.com",
                "seendate": "20240115T130000Z",
            },
            {"title": "Bad", "url": "notaurl", "domain": "x.com"},
            {
                "title": "Chip demand",
                "url": "https://news.example.org/b",
                "domain": "news.example.org",
                "seendate": "20240116T090000Z",
            },
        ]
    )
    assert len(articles) == 2
    assert articles[0].url == "https://Example.com/news/a/"
    assert canonical_url(articles[0].url) == "https://example.com/news/a"
    assert articles[0].published_at == datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)


def test_news_agent_no_evidence(monkeypatch) -> None:
    class EmptyProvider:
        def fetch(self, ticker, company_name, max_records=20):
            return []

    result = analyze_news(Ticker.AAPL, provider=EmptyProvider())  # type: ignore[arg-type]
    assert result.status == "no_evidence"
    assert result.articles == []


def test_news_agent_schema_success(monkeypatch) -> None:
    from app.providers.news_provider import NormalizedArticle

    class Provider:
        def fetch(self, ticker, company_name, max_records=20):
            return [
                NormalizedArticle(
                    title="Apple announces product",
                    source="example.com",
                    published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
                    url="https://example.com/a",
                )
            ]

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()


def test_news_agent_rejects_invalid_structured_output(monkeypatch) -> None:
    from app.providers.news_provider import NormalizedArticle

    class Provider:
        def fetch(self, ticker, company_name, max_records=20):
            return [NormalizedArticle("Headline", "example.com", None, "https://example.com/a")]

    class InvalidStructured:
        def invoke(self, _messages):
            return {"overall_sentiment": "uncertain"}

    class InvalidLLM:
        def with_structured_output(self, _schema, method="json_schema"):
            return InvalidStructured()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    result = analyze_news(Ticker.AAPL, provider=Provider(), llm=InvalidLLM())  # type: ignore[arg-type]
    assert result.status == "failed"
    assert result.articles[0].url == "https://example.com/a"
    get_settings.cache_clear()
    llm_out = NewsLlmOutput(
        overall_sentiment="positive",
        confidence="Low: headlines only",
        positive_catalysts=["Product announcement"],
        negative_catalysts=["None stated"],
        major_developments=["Product announcement"],
        investor_relevance="May affect near-term attention, not a return forecast.",
        evidence_limitations="Headlines and metadata only.",
    )
    result = analyze_news(Ticker.AAPL, provider=Provider(), llm=FakeLLM(llm_out))  # type: ignore[arg-type]
    assert isinstance(result, NewsAnalysis)
    assert result.status == "succeeded"
    assert result.articles[0].url == "https://example.com/a"
    assert result.overall_sentiment == "positive"
    get_settings.cache_clear()


def test_gdelt_html_response_is_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>nope</html>")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = GdeltNewsProvider(client=client)
    try:
        provider.fetch(Ticker.AAPL, "Apple Inc.")
        raise AssertionError("expected ProviderError")
    except Exception as exc:
        from app.utils.errors import ProviderError

        assert isinstance(exc, ProviderError)


def test_gdelt_rate_limit_is_reported_explicitly() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GdeltNewsProvider(client=client)
    try:
        provider.fetch(Ticker.AAPL, "Apple Inc.")
        raise AssertionError("expected rate-limit error")
    except Exception as exc:
        from app.utils.errors import ProviderError

        assert isinstance(exc, ProviderError)
        assert "rate limited" in str(exc)
    finally:
        client.close()
