from typing import TypedDict

from app.api.schemas import (
    ChartSeries,
    FundamentalAnalysis,
    NewsAnalysis,
    ResearchSummary,
    TechnicalAnalysis,
    Ticker,
)


class ResearchState(TypedDict, total=False):
    ticker: Ticker
    news: NewsAnalysis
    technical: TechnicalAnalysis
    fundamental: FundamentalAnalysis
    chart: ChartSeries
    summary: ResearchSummary
