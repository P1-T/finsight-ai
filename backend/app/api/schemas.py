from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ChatHistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=1200)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=1200)
    history: list[ChatHistoryTurn] = Field(default_factory=list, max_length=8)

    @field_validator("prompt")
    @classmethod
    def non_blank_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt must not be blank.")
        return value.strip()


CompanyQuery = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
MetricName = Literal[
    "latest_close",
    "daily_pct_change",
    "return_5d",
    "return_20d",
    "sma20",
    "sma50",
    "rsi14",
    "volume_vs_average",
    "volatility_note",
]
Period = Literal["1mo", "3mo", "6mo", "1y"]
Recency = Literal["day", "week", "month", "year"]
ResponseTemplate = Literal[
    "company_analysis",
    "stock_comparison",
    "news_analysis",
    "technical_analysis",
    "quarterly_performance",
    "research_answer",
    "valuation_analysis",
    "dividend_analysis",
    "risk_analysis",
    "sector_analysis",
    "forward_outlook",
    "earnings_preview",
    "revenue_analysis",
    "growth_analysis",
    "profitability_analysis",
    "cash_flow_analysis",
    "balance_sheet_analysis",
    "valuation_comparison",
    "price_momentum",
    "trend_analysis",
    "support_resistance",
    "volume_analysis",
    "market_reaction",
    "catalyst_analysis",
    "analyst_sentiment",
    "insider_activity",
    "institutional_ownership",
    "short_interest",
    "options_activity",
    "macro_sensitivity",
]
VisualComponentType = Literal[
    "company_header",
    "metric_grid",
    "price_chart",
    "fundamental_cards",
    "scenario_cards",
    "news_timeline",
    "comparison_table",
    "fact_grid",
    "data_chart",
    "takeaways",
    "answer_card",
]


class MarketDataAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Period = "6mo"
    metrics: list[MetricName] = Field(default_factory=lambda: ["latest_close", "daily_pct_change", "return_5d", "return_20d"], max_length=9)


class SearchAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=500)
    result_limit: int = Field(default=5, ge=1, le=5)
    recency: Recency = "week"


class ResearchPlan(BaseModel):
    """Strict first-pass Claude response that selects tools and a response template."""

    model_config = ConfigDict(extra="forbid")

    intent: Literal["general", "company_research", "market_data", "news", "comparison", "earnings", "educational", "other"]
    template_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{1,63}$")
    response_template: ResponseTemplate = "research_answer"
    companies: list[CompanyQuery] = Field(default_factory=list, max_length=6)
    market_data: MarketDataAction | None = None
    web_search: list[SearchAction] = Field(default_factory=list, max_length=2)
    news_search: list[SearchAction] = Field(default_factory=list, max_length=2)
    visual_components: list[VisualComponentType] = Field(default_factory=list, max_length=9)
    clarification_question: str | None = Field(default=None, max_length=300)
    unsupported_data_needs: list[str] = Field(default_factory=list, max_length=6)


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=700)
    source_ids: list[str] = Field(default_factory=list, max_length=8)


class CompanyInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=15)
    summary: str = Field(min_length=1, max_length=500)
    source_ids: list[str] = Field(default_factory=list, max_length=8)


class SentimentInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=15)
    sentiment: Literal["positive", "neutral", "negative", "mixed"]
    rationale: str = Field(min_length=1, max_length=500)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class CompanyAnalysisNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=600)
    source_ids: list[str] = Field(default_factory=list, max_length=15)
    positive_drivers: list[EvidenceClaim] = Field(default_factory=list, max_length=4)
    risks: list[EvidenceClaim] = Field(default_factory=list, max_length=4)


class StockComparisonNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    source_ids: list[str] = Field(default_factory=list, max_length=15)
    company_views: list[CompanyInsight] = Field(default_factory=list, max_length=6)
    comparison_points: list[EvidenceClaim] = Field(default_factory=list, max_length=6)


class NewsAnalysisNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    source_ids: list[str] = Field(default_factory=list, max_length=15)
    company_sentiment: list[SentimentInsight] = Field(default_factory=list, max_length=6)


class TechnicalAnalysisNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    source_ids: list[str] = Field(default_factory=list, max_length=15)
    observations: list[EvidenceClaim] = Field(default_factory=list, max_length=6)


class FinancialFact(BaseModel):
    """A numeric reported fact whose source quote is checked against retrieved evidence."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    value: float
    range_end: float | None = None
    unit: Literal["percent", "USD", "EUR", "USD_billions", "EUR_billions", "USD_millions", "EUR_millions", "count"]
    fact_kind: Literal["reported", "guidance"] = "reported"
    comparison_value: float | None = None
    comparison_label: str | None = Field(default=None, max_length=60)
    period: str = Field(min_length=1, max_length=60)
    source_ids: list[str] = Field(min_length=1, max_length=4)
    evidence_quote: str = Field(min_length=12, max_length=280)

    @model_validator(mode="after")
    def valid_numeric_range(self) -> FinancialFact:
        if self.range_end is not None and self.range_end < self.value:
            raise ValueError("range_end must be greater than or equal to value")
        return self


class QuarterlyPerformanceNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=420)
    period: str = Field(min_length=1, max_length=80)
    reported_facts: list[FinancialFact] = Field(default_factory=list, max_length=10)
    positive_drivers: list[EvidenceClaim] = Field(default_factory=list, max_length=4)
    risks: list[EvidenceClaim] = Field(default_factory=list, max_length=4)
    source_ids: list[str] = Field(default_factory=list, max_length=15)


class ResearchAnswerNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=4000)
    source_ids: list[str] = Field(default_factory=list, max_length=15)


class ClarificationNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1000)


class CompanyIdentity(BaseModel):
    ticker: str
    name: str
    exchange: str


class CompanySearchResponse(BaseModel):
    companies: list[CompanyIdentity] = Field(default_factory=list)


class MarketMetric(BaseModel):
    key: MetricName
    value: float | str
    unit: Literal["usd", "percent", "index", "text"]


class SourceReference(BaseModel):
    id: str
    title: str
    provider: str
    url: str | None = None
    published_at: str | None = None
    company_tickers: list[str] = Field(default_factory=list)


class PricePoint(BaseModel):
    date: str
    close: float


class MarketSnapshot(BaseModel):
    ticker: str
    as_of_date: str
    period: Period
    metrics: list[MarketMetric]
    source_id: str
    price_series: list[PricePoint] = Field(default_factory=list)


class DataProvenance(BaseModel):
    kind: Literal["live", "illustrative", "mixed", "unavailable"]
    label: str
    as_of: str | None = None


class CompanyHeaderBlock(BaseModel):
    type: Literal["company_header"]
    company: CompanyIdentity
    description: str
    provenance: DataProvenance


class VisualMetric(BaseModel):
    label: str
    value: str
    detail: str | None = None


class MetricGridBlock(BaseModel):
    type: Literal["metric_grid"]
    title: str
    metrics: list[VisualMetric]
    provenance: DataProvenance


class PriceChartBlock(BaseModel):
    type: Literal["price_chart"]
    title: str
    points: list[PricePoint]
    provenance: DataProvenance


class FundamentalMetric(BaseModel):
    label: str
    value: str
    detail: str


class FundamentalCardsBlock(BaseModel):
    type: Literal["fundamental_cards"]
    title: str
    metrics: list[FundamentalMetric]
    provenance: DataProvenance


class FactGridMetric(BaseModel):
    label: str
    value: str
    detail: str | None = None
    range_low: str | None = None
    range_high: str | None = None
    source_ids: list[str] = Field(default_factory=list)


class FactGridBlock(BaseModel):
    type: Literal["fact_grid"]
    title: str
    period: str
    metrics: list[FactGridMetric] = Field(max_length=10)
    provenance: DataProvenance


class DataChartDatum(BaseModel):
    label: str
    value: float
    source_ids: list[str] = Field(default_factory=list)


class DataChartBlock(BaseModel):
    type: Literal["data_chart"]
    chart_type: Literal["line", "bar", "donut"]
    title: str
    unit: Literal["percent", "USD", "EUR", "USD_billions", "EUR_billions", "USD_millions", "EUR_millions", "count"]
    data: list[DataChartDatum] = Field(min_length=2, max_length=24)
    provenance: DataProvenance
    source_ids: list[str] = Field(default_factory=list)


class ScenarioPoint(BaseModel):
    title: str
    detail: str
    provenance: DataProvenance
    source_ids: list[str] = Field(default_factory=list)


class ScenarioCardsBlock(BaseModel):
    type: Literal["scenario_cards"]
    scenario: Literal["bull", "bear"]
    title: str
    points: list[ScenarioPoint] = Field(min_length=1, max_length=4)


class TimelineItem(BaseModel):
    title: str
    detail: str
    date: str | None = None
    url: str | None = None
    provenance: DataProvenance


class NewsTimelineBlock(BaseModel):
    type: Literal["news_timeline"]
    title: str
    items: list[TimelineItem]


class ComparisonRow(BaseModel):
    ticker: str
    name: str
    latest_close: str
    daily_change: str
    period_return: str
    revenue_growth: str
    margin: str


class ComparisonTableBlock(BaseModel):
    type: Literal["comparison_table"]
    title: str
    rows: list[ComparisonRow]
    provenance: DataProvenance


class TakeawaysBlock(BaseModel):
    type: Literal["takeaways"]
    title: str
    items: list[str]


class AnswerCardBlock(BaseModel):
    type: Literal["answer_card"]
    title: str
    body: str


VisualBlock = Annotated[
    Union[
        CompanyHeaderBlock,
        MetricGridBlock,
        PriceChartBlock,
        FundamentalCardsBlock,
        ScenarioCardsBlock,
        NewsTimelineBlock,
        ComparisonTableBlock,
        FactGridBlock,
        DataChartBlock,
        TakeawaysBlock,
        AnswerCardBlock,
    ],
    Field(discriminator="type"),
]


class VisualResearchResponse(BaseModel):
    schema_version: Literal[3] = 3
    template: ResponseTemplate | Literal["clarification"]
    intent_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{1,63}$")
    intent_confidence: float | None = Field(default=None, ge=0, le=1)
    title: str
    summary: str
    blocks: list[VisualBlock] = Field(default_factory=list, max_length=12)
    sources: list[SourceReference] = Field(default_factory=list)
    unresolved_company_query: str | None = None
    company_suggestions: list[CompanyIdentity] = Field(default_factory=list, max_length=8)
    generated_by: Literal["claude", "fallback"]


class NewsArticle(BaseModel):
    source_id: str
    title: str
    source: str | None = None
    published_at: str | None = None
    url: str
    snippet: str | None = None
    company_tickers: list[str] = Field(default_factory=list)


class NewsCoverage(BaseModel):
    ticker: str
    relevant_result_count: int = Field(ge=0)


class ResponseBase(BaseModel):
    schema_version: Literal[1] = 1
    title: str
    companies: list[CompanyIdentity] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CompanyAnalysisResponse(ResponseBase):
    template: Literal["company_analysis"]
    company: CompanyIdentity
    market_snapshot: MarketSnapshot | None = None
    news_articles: list[NewsArticle] = Field(default_factory=list)
    news_coverage: list[NewsCoverage] = Field(default_factory=list)
    narrative: CompanyAnalysisNarrative


class StockComparisonResponse(ResponseBase):
    template: Literal["stock_comparison"]
    market_snapshots: list[MarketSnapshot] = Field(default_factory=list)
    news_articles: list[NewsArticle] = Field(default_factory=list)
    news_coverage: list[NewsCoverage] = Field(default_factory=list)
    narrative: StockComparisonNarrative


class NewsAnalysisResponse(ResponseBase):
    template: Literal["news_analysis"]
    news_articles: list[NewsArticle] = Field(default_factory=list)
    news_coverage: list[NewsCoverage] = Field(default_factory=list)
    narrative: NewsAnalysisNarrative


class TechnicalAnalysisResponse(ResponseBase):
    template: Literal["technical_analysis"]
    market_snapshots: list[MarketSnapshot] = Field(default_factory=list)
    narrative: TechnicalAnalysisNarrative


class QuarterlyPerformanceResponse(ResponseBase):
    template: Literal["quarterly_performance"]
    company: CompanyIdentity
    market_snapshot: MarketSnapshot | None = None
    narrative: QuarterlyPerformanceNarrative


class ResearchAnswerResponse(ResponseBase):
    template: Literal[
        "research_answer", "valuation_analysis", "dividend_analysis", "risk_analysis", "sector_analysis",
        "forward_outlook", "earnings_preview", "revenue_analysis", "growth_analysis",
        "profitability_analysis", "cash_flow_analysis", "balance_sheet_analysis", "valuation_comparison",
        "price_momentum", "trend_analysis", "support_resistance", "volume_analysis", "market_reaction",
        "catalyst_analysis", "analyst_sentiment", "insider_activity", "institutional_ownership",
        "short_interest", "options_activity", "macro_sensitivity",
    ]
    narrative: ResearchAnswerNarrative


class ClarificationResponse(ResponseBase):
    template: Literal["clarification"]
    narrative: ClarificationNarrative
    unresolved_company_query: str | None = None
    company_suggestions: list[CompanyIdentity] = Field(default_factory=list, max_length=8)


LegacyResearchResponse = Annotated[
    Union[
        CompanyAnalysisResponse,
        StockComparisonResponse,
        NewsAnalysisResponse,
        TechnicalAnalysisResponse,
        QuarterlyPerformanceResponse,
        ResearchAnswerResponse,
        ClarificationResponse,
    ],
    Field(discriminator="template"),
]
ResearchResponse = Union[VisualResearchResponse, LegacyResearchResponse]


class MetricValue(BaseModel):
    value: float | None = None
    unavailable_reason: str | None = None


ToolName = Literal["market_data", "web_search", "news_search"]
ToolStatus = Literal["running", "succeeded", "failed", "no_evidence"]


class ToolStatusEvent(BaseModel):
    tool: ToolName
    status: ToolStatus
    detail: str | None = None


class ResearchStageEvent(BaseModel):
    stage: Literal["planning", "research", "synthesis"]
    label: str
