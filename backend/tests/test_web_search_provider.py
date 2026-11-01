import sys
from types import ModuleType

from app.config import Settings
from app.providers.web_search_provider import DDGSWebSearchProvider


def test_ddgs_provider_normalizes_deduplicates_and_limits_results(monkeypatch) -> None:
    captured: dict = {}

    class FakeDDGS:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def news(self, **kwargs):
            captured.update(kwargs)
            return [
                {"title": "Company results", "url": "https://example.com/story#top", "source": "Example", "date": "2026-10-28T12:00:00Z", "body": "Headline excerpt"},
                {"title": "Company results", "url": "https://example.com/duplicate", "source": "Example"},
                {"title": "Invalid", "url": "javascript:alert(1)"},
            ]

        def text(self, **kwargs):
            captured.update(kwargs)
            return [
                {"title": "Company profile", "href": "https://example.com/profile", "body": "Business overview"},
                {"title": "Invalid", "href": "javascript:alert(1)"},
            ]

    monkeypatch.setitem(sys.modules, "ddgs", ModuleType("ddgs"))
    sys.modules["ddgs"].DDGS = FakeDDGS
    results = DDGSWebSearchProvider(Settings(web_search_timeout_seconds=3)).search("company overview", 20)
    assert captured["timeout"] == 3
    assert captured["region"] == "us-en"
    assert captured["max_results"] == 5
    assert len(results) == 1
    assert results[0].url == "https://example.com/profile"
    assert results[0].source == "example.com"
    assert results[0].excerpt == "Business overview"

    news = DDGSWebSearchProvider(Settings(web_search_timeout_seconds=3)).search("latest news", 5, "news")
    assert captured["timelimit"] == "w"
    assert len(news) == 1
    results = news
    assert len(results) == 1
    assert results[0].url == "https://example.com/story"
    assert results[0].source == "Example"
    assert results[0].published_at is not None
    assert results[0].excerpt == "Headline excerpt"
