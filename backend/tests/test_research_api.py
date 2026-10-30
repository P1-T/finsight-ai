import asyncio
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.schemas import (
    ChartSeries,
    MetricValue,
    NewsAnalysis,
    NewsArticle,
    ResearchResponse,
    ResearchSummary,
    TechnicalAnalysis,
    Ticker,
)
from app.constants import DISCLAIMER


def _response(*, news: NewsAnalysis, technical: TechnicalAnalysis) -> ResearchResponse:
    return ResearchResponse(
        ticker=Ticker.AAPL,
        company_name="Apple Inc.",
        generated_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        news=news,
        technical=technical,
        chart=ChartSeries(),
        summary=ResearchSummary(
            news_perspective="n",
            technical_perspective="t",
            agreement="a",
            disagreement="d",
            missing_information="m",
        ),
        disclaimer=DISCLAIMER,
    )


def test_invalid_ticker(client: TestClient) -> None:
    response = client.post("/api/research", json={"ticker": "TSLA"})
    assert response.status_code == 422


def test_partial_success(client: TestClient, monkeypatch) -> None:
    async def fake_run(ticker: Ticker) -> ResearchResponse:
        return _response(
            news=NewsAnalysis(
                status="succeeded",
                overall_sentiment="neutral",
                articles=[
                    NewsArticle(
                        title="Apple event",
                        source="example.com",
                        published_at=datetime(2024, 5, 31, tzinfo=timezone.utc),
                        url="https://example.com/news",
                    )
                ],
            ),
            technical=TechnicalAnalysis(status="failed", error="Market data provider unavailable."),
        )

    monkeypatch.setattr("app.api.routes.run_research", fake_run)
    response = client.post("/api/research", json={"ticker": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["news"]["status"] == "succeeded"
    assert body["technical"]["status"] == "failed"
    assert "api_key" not in str(body).lower()


def test_both_agents_fail(client: TestClient, monkeypatch) -> None:
    async def fake_run(ticker: Ticker) -> ResearchResponse:
        result = _response(
            news=NewsAnalysis(status="failed", error="GDELT unavailable."),
            technical=TechnicalAnalysis(status="failed", error="yfinance unavailable."),
        )
        result.fundamental.status = "failed"
        result.fundamental.error = "Pinecone unavailable."
        return result

    monkeypatch.setattr("app.api.routes.run_research", fake_run)
    response = client.post("/api/research", json={"ticker": "AAPL"})
    assert response.status_code == 502
    body = response.json()
    assert body["news"]["status"] == "failed"
    assert body["technical"]["status"] == "failed"


def test_missing_api_key(client: TestClient, monkeypatch) -> None:
    import pandas as pd

    from app.agents import news_agent, technical_agent
    from app.config import get_settings
    from app.providers.market_data_provider import MarketHistory
    from app.providers.news_provider import NormalizedArticle

    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()

    class NewsProvider:
        def fetch(self, ticker, company_name, max_records=20):
            return [
                NormalizedArticle(
                    title="Headline",
                    source="example.com",
                    published_at=None,
                    url="https://example.com/a",
                )
            ]

    class MarketProvider:
        def fetch(self, ticker):
            index = pd.date_range("2024-01-02", periods=60, freq="B", tz=timezone.utc)
            values = [100.0 + i for i in range(60)]
            frame = pd.DataFrame(
                {
                    "Open": values,
                    "High": values,
                    "Low": values,
                    "Close": values,
                    "Volume": [1_000_000.0] * 60,
                },
                index=index,
            )
            return MarketHistory(ticker=ticker, frame=frame, as_of_date=index[-1].date())

    monkeypatch.setattr(news_agent, "MarketNewsApiProvider", lambda: NewsProvider())
    monkeypatch.setattr(technical_agent, "YFinanceMarketDataProvider", lambda: MarketProvider())

    from app.graph.research_graph import news_node, technical_node

    news = news_node({"ticker": Ticker.AAPL})["news"]
    technical = technical_node({"ticker": Ticker.AAPL})["technical"]
    assert news.status == "failed"
    assert "API key" in (news.error or "")
    assert technical.status == "failed"
    assert "API key" in (technical.error or "")
    get_settings.cache_clear()


def test_upstream_provider_failure_isolated(client: TestClient, monkeypatch) -> None:
    async def fake_run(ticker: Ticker) -> ResearchResponse:
        return _response(
            news=NewsAnalysis(status="failed", error="News source (MarketNewsAPI) is unavailable or returned an error."),
            technical=TechnicalAnalysis(
                status="succeeded",
                as_of_date=date(2024, 5, 31),
                latest_close=MetricValue(value=192.4),
            ),
        )

    monkeypatch.setattr("app.api.routes.run_research", fake_run)
    response = client.post("/api/research", json={"ticker": "NVDA"})
    assert response.status_code == 200
    assert response.json()["technical"]["latest_close"]["value"] == 192.4


def test_research_timeout_is_reported_safely(client: TestClient, monkeypatch) -> None:
    async def fake_run(ticker: Ticker) -> ResearchResponse:
        raise asyncio.TimeoutError

    monkeypatch.setattr("app.api.routes.run_research", fake_run)
    response = client.post("/api/research", json={"ticker": "AAPL"})
    assert response.status_code == 504
    assert "time limit" in response.json()["detail"]
