from __future__ import annotations

import asyncio
import logging

from langgraph.graph import END, START, StateGraph

from app.agents.fundamental_agent import analyze_fundamental
from app.agents.news_agent import analyze_news
from app.agents.technical_agent import analyze_technical
from app.api.schemas import FundamentalAnalysis, Ticker
from app.graph.state import ResearchState
from app.services.summary_service import combine_summary

logger = logging.getLogger(__name__)


def news_node(state: ResearchState) -> dict:
    ticker: Ticker = state["ticker"]
    try:
        news = analyze_news(ticker)
    except Exception:
        logger.exception("Unexpected news agent failure for %s", ticker.value)
        from app.api.schemas import NewsAnalysis

        news = NewsAnalysis(status="failed", error="News analysis could not be completed.")
    return {"news": news}


def technical_node(state: ResearchState) -> dict:
    ticker: Ticker = state["ticker"]
    try:
        technical, chart = analyze_technical(ticker)
    except Exception:
        logger.exception("Unexpected technical agent failure for %s", ticker.value)
        from app.api.schemas import ChartSeries, TechnicalAnalysis

        technical, chart = (
            TechnicalAnalysis(status="failed", error="Technical analysis could not be completed."),
            ChartSeries(),
        )
    return {"technical": technical, "chart": chart}


def fundamental_node(state: ResearchState) -> dict:
    ticker: Ticker = state["ticker"]
    try:
        fundamental = analyze_fundamental(ticker)
    except Exception:
        logger.exception("Unexpected fundamental agent failure for %s", ticker.value)
        fundamental = FundamentalAnalysis(status="failed", error="Fundamental analysis could not be completed.")
    return {"fundamental": fundamental}


def combine_node(state: ResearchState) -> dict:
    from app.api.schemas import FundamentalAnalysis

    fundamental = state.get("fundamental") or FundamentalAnalysis(status="no_evidence")
    summary = combine_summary(state["news"], state["technical"], fundamental)
    return {"summary": summary}


def build_research_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("news_agent", news_node)
    graph.add_node("technical_agent", technical_node)
    graph.add_node("fundamental_agent", fundamental_node)
    graph.add_node("combine", combine_node)
    graph.add_edge(START, "news_agent")
    graph.add_edge(START, "technical_agent")
    graph.add_edge(START, "fundamental_agent")
    graph.add_edge("news_agent", "combine")
    graph.add_edge("technical_agent", "combine")
    graph.add_edge("fundamental_agent", "combine")
    graph.add_edge("combine", END)
    return graph.compile()


research_graph = build_research_graph()


async def run_graph(ticker: Ticker) -> ResearchState:
    return await asyncio.to_thread(research_graph.invoke, {"ticker": ticker})
