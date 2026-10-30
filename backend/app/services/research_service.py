from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.api.schemas import (
    SUPPORTED_STOCKS,
    ChartSeries,
    FundamentalAnalysis,
    NewsAnalysis,
    ResearchResponse,
    ResearchSummary,
    TechnicalAnalysis,
    Ticker,
)
from app.config import get_settings
from app.constants import DISCLAIMER
from app.graph.research_graph import run_graph

logger = logging.getLogger(__name__)


async def run_research(ticker: Ticker) -> ResearchResponse:
    settings = get_settings()
    try:
        state = await asyncio.wait_for(
            run_graph(ticker),
            timeout=settings.research_timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning("Research workflow timed out for %s", ticker.value)
        raise
    news = state.get("news") or NewsAnalysis(status="failed", error="News agent produced no result.")
    technical = state.get("technical") or TechnicalAnalysis(
        status="failed", error="Technical agent produced no result."
    )
    fundamental = state.get("fundamental") or FundamentalAnalysis(
        status="failed", error="Fundamental agent produced no result."
    )
    chart = state.get("chart") or ChartSeries()
    summary = state.get("summary") or ResearchSummary(
        news_perspective="News analysis was unavailable.",
        technical_perspective="Technical analysis was unavailable.",
        fundamental_perspective="Fundamental analysis was unavailable.",
        agreement="Agreement cannot be assessed.",
        disagreement="Divergence cannot be assessed.",
        missing_information="The workflow did not produce a combined summary.",
    )
    return ResearchResponse(
        ticker=ticker,
        company_name=SUPPORTED_STOCKS[ticker],
        generated_at=datetime.now(timezone.utc),
        news=news,
        technical=technical,
        fundamental=fundamental,
        chart=chart,
        summary=summary,
        disclaimer=DISCLAIMER,
    )
