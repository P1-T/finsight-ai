from app.api.schemas import (
    ChartSeries,
    MetricValue,
    NewsAnalysis,
    TechnicalAnalysis,
    Ticker,
)
from app.graph.research_graph import build_research_graph, combine_node
from app.services.summary_service import combine_summary


def test_summary_partial_news_only() -> None:
    news = NewsAnalysis(
        status="succeeded",
        overall_sentiment="mixed",
        investor_relevance="Headlines were mixed.",
        evidence_limitations="Headlines only.",
    )
    technical = TechnicalAnalysis(status="failed", error="yfinance unavailable")
    summary = combine_summary(news, technical)
    assert "mixed" in summary.news_perspective
    assert "unavailable" in summary.technical_perspective.lower()
    assert "cannot be assessed" in summary.agreement.lower()
    assert "yfinance" in summary.missing_information


def test_summary_does_not_invent_agreement_when_both_fail() -> None:
    news = NewsAnalysis(status="failed", error="GDELT down")
    technical = TechnicalAnalysis(status="failed", error="LLM down")
    summary = combine_summary(news, technical)
    assert "Neither agent" in summary.agreement
    assert "GDELT" in summary.missing_information


def test_combine_node_uses_python_only() -> None:
    state = {
        "ticker": Ticker.AAPL,
        "news": NewsAnalysis(status="no_evidence", evidence_limitations="No articles."),
        "technical": TechnicalAnalysis(
            status="succeeded",
            latest_close=MetricValue(value=100.0),
            short_term_trend="Above SMA20",
        ),
        "chart": ChartSeries(),
    }
    result = combine_node(state)
    assert "No relevant articles" in result["summary"].news_perspective
    assert "Above SMA20" in result["summary"].technical_perspective


def test_langgraph_runs_both_agents_and_combines(monkeypatch) -> None:
    from app.agents import news_agent, technical_agent

    monkeypatch.setattr(
        news_agent,
        "analyze_news",
        lambda _ticker: NewsAnalysis(status="succeeded", overall_sentiment="neutral"),
    )
    monkeypatch.setattr(
        technical_agent,
        "analyze_technical",
        lambda _ticker: (
            TechnicalAnalysis(status="succeeded", short_term_trend="Sideways"),
            ChartSeries(),
        ),
    )
    from app.api.schemas import FundamentalAnalysis
    from app.graph import research_graph

    monkeypatch.setattr(research_graph, "analyze_news", news_agent.analyze_news)
    monkeypatch.setattr(research_graph, "analyze_technical", technical_agent.analyze_technical)
    monkeypatch.setattr(
        research_graph,
        "analyze_fundamental",
        lambda _ticker: FundamentalAnalysis(status="no_evidence", error="No indexed filing in test."),
    )
    result = build_research_graph().invoke({"ticker": Ticker.AAPL})
    assert result["news"].status == "succeeded"
    assert result["technical"].short_term_trend == "Sideways"
    assert result["summary"].agreement
