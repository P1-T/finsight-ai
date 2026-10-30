from datetime import date, datetime
from enum import Enum
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class Ticker(str, Enum):
    AAPL = "AAPL"
    NVDA = "NVDA"
    MSFT = "MSFT"


SUPPORTED_STOCKS: dict[Ticker, str] = {
    Ticker.AAPL: "Apple Inc.",
    Ticker.NVDA: "NVIDIA Corporation",
    Ticker.MSFT: "Microsoft Corporation",
}

AgentStatus = Literal["succeeded", "failed", "no_evidence"]
SentimentLabel = Literal["positive", "neutral", "negative", "mixed"]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class StockInfo(BaseModel):
    ticker: Ticker
    name: str


class StocksResponse(BaseModel):
    stocks: list[StockInfo]


class ResearchRequest(BaseModel):
    ticker: Ticker


class NewsArticle(BaseModel):
    title: str
    source: str | None = None
    published_at: datetime | None = None
    url: str

    @field_validator("url")
    @classmethod
    def validate_original_http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or any(character.isspace() for character in value)
        ):
            raise ValueError("Article URL must be an absolute HTTP or HTTPS URL.")
        return value


class NewsAnalysis(BaseModel):
    status: AgentStatus
    error: str | None = None
    overall_sentiment: SentimentLabel | None = None
    confidence: str | None = None
    positive_catalysts: list[str] = Field(default_factory=list)
    negative_catalysts: list[str] = Field(default_factory=list)
    major_developments: list[str] = Field(default_factory=list)
    investor_relevance: str | None = None
    evidence_limitations: str | None = None
    lookback: str | None = None
    articles: list[NewsArticle] = Field(default_factory=list)


class MetricValue(BaseModel):
    value: float | None = None
    unavailable_reason: str | None = None


class TechnicalAnalysis(BaseModel):
    status: AgentStatus
    error: str | None = None
    as_of_date: date | None = None
    latest_close: MetricValue = Field(default_factory=MetricValue)
    daily_pct_change: MetricValue = Field(default_factory=MetricValue)
    return_5d: MetricValue = Field(default_factory=MetricValue)
    return_20d: MetricValue = Field(default_factory=MetricValue)
    sma20: MetricValue = Field(default_factory=MetricValue)
    sma50: MetricValue = Field(default_factory=MetricValue)
    rsi14: MetricValue = Field(default_factory=MetricValue)
    volume_vs_average: str | None = None
    volatility_note: str | None = None
    short_term_trend: str | None = None
    medium_term_trend: str | None = None
    momentum: str | None = None
    caveats: list[str] = Field(default_factory=list)


class FundamentalMetric(BaseModel):
    value: float | None = None
    unit: str | None = None
    fiscal_year: int | None = None
    unavailable_reason: str | None = None


class FilingCitation(BaseModel):
    section: str
    excerpt: str
    url: str


class FundamentalFinding(BaseModel):
    topic: str
    finding: str
    citation_urls: list[str] = Field(default_factory=list)


class FundamentalAnalysis(BaseModel):
    status: AgentStatus
    error: str | None = None
    filing_date: date | None = None
    fiscal_year: int | None = None
    filing_url: str | None = None
    revenue: FundamentalMetric = Field(default_factory=FundamentalMetric)
    revenue_yoy_growth_pct: FundamentalMetric = Field(default_factory=FundamentalMetric)
    operating_margin_pct: FundamentalMetric = Field(default_factory=FundamentalMetric)
    net_margin_pct: FundamentalMetric = Field(default_factory=FundamentalMetric)
    operating_cash_flow: FundamentalMetric = Field(default_factory=FundamentalMetric)
    capital_expenditures: FundamentalMetric = Field(default_factory=FundamentalMetric)
    free_cash_flow: FundamentalMetric = Field(default_factory=FundamentalMetric)
    cash_and_equivalents: FundamentalMetric = Field(default_factory=FundamentalMetric)
    overview: str | None = None
    business_findings: list[FundamentalFinding] = Field(default_factory=list)
    key_risks: list[FundamentalFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    citations: list[FilingCitation] = Field(default_factory=list)


class ChartPoint(BaseModel):
    time: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class OverlayPoint(BaseModel):
    time: date
    value: float


class ChartSeries(BaseModel):
    candles: list[ChartPoint] = Field(default_factory=list)
    sma20: list[OverlayPoint] = Field(default_factory=list)
    sma50: list[OverlayPoint] = Field(default_factory=list)


class ResearchSummary(BaseModel):
    news_perspective: str
    technical_perspective: str
    fundamental_perspective: str = "Fundamental perspective unavailable."
    agreement: str
    disagreement: str
    missing_information: str


class ResearchResponse(BaseModel):
    ticker: Ticker
    company_name: str
    generated_at: datetime
    news: NewsAnalysis
    technical: TechnicalAnalysis
    fundamental: FundamentalAnalysis = Field(default_factory=lambda: FundamentalAnalysis(status="no_evidence"))
    chart: ChartSeries
    summary: ResearchSummary
    disclaimer: str
