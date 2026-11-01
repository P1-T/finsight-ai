from __future__ import annotations

from typing import Any

from app.api.schemas import (
    AnswerCardBlock,
    CompanyAnalysisResponse,
    CompanyHeaderBlock,
    CompanyIdentity,
    ComparisonRow,
    ComparisonTableBlock,
    DataProvenance,
    FundamentalCardsBlock,
    FundamentalMetric,
    MarketMetric,
    MetricGridBlock,
    NewsAnalysisResponse,
    NewsTimelineBlock,
    PriceChartBlock,
    PricePoint,
    ScenarioCardsBlock,
    ScenarioPoint,
    StockComparisonResponse,
    TakeawaysBlock,
    TimelineItem,
    VisualMetric,
    VisualResearchResponse,
)
from app.providers.company_directory import Company
from app.services.demo_data import synthetic_dataset
from app.services.technical_indicators import compute_metrics

_MARKET_KEYS = {"latest_close", "daily_pct_change", "return_5d", "return_20d", "sma20", "sma50"}
_MARKET_LABELS = {
    "latest_close": "Latest close",
    "daily_pct_change": "Daily change",
    "return_5d": "5-session return",
    "return_20d": "20-session return",
    "sma20": "SMA 20",
    "sma50": "SMA 50",
}
_COMPANY_DEFAULT = [
    "company_header", "metric_grid", "price_chart", "fundamental_cards",
    "scenario_cards", "news_timeline",
]


def _format_metric(metric: MarketMetric) -> str:
    value = metric.value
    if isinstance(value, str):
        return value
    if metric.unit == "usd":
        return f"${value:,.2f}"
    if metric.unit == "percent":
        return f"{value:+.2f}%"
    return f"{value:,.2f}"


def _snapshot_metrics(snapshot: Any | None, demo: dict[str, Any]) -> tuple[list[MarketMetric], list[PricePoint], DataProvenance]:
    if snapshot and snapshot.metrics and snapshot.price_series:
        metrics = [metric for metric in snapshot.metrics if metric.key in _MARKET_KEYS]
        points = snapshot.price_series
        return metrics, points, DataProvenance(kind="live", label="Historical market data", as_of=snapshot.as_of_date)

    computed = compute_metrics(demo["frame"])
    metrics: list[MarketMetric] = []
    for key in _MARKET_KEYS:
        raw = computed[key]
        value = raw.value if hasattr(raw, "value") else raw
        if value is None:
            continue
        unit = "usd" if key in {"latest_close", "sma20", "sma50"} else "percent"
        metrics.append(MarketMetric(key=key, value=value, unit=unit))
    points = [PricePoint.model_validate(item) for item in demo["points"]]
    return metrics, points, DataProvenance(kind="illustrative", label="Illustrative data", as_of=demo["as_of"])


def _narrative_summary(response: Any) -> str:
    narrative = response.narrative
    return str(getattr(narrative, "summary", getattr(narrative, "answer", getattr(narrative, "question", ""))))


def _company_identity(company: Any) -> CompanyIdentity:
    return CompanyIdentity(ticker=company.ticker, name=company.name, exchange=company.exchange)


def _scenario_block(response: Any, companies: list[Company], scenario: str) -> ScenarioCardsBlock:
    demo = synthetic_dataset(companies[0].ticker)
    narrative = response.narrative
    supported = []
    if isinstance(response, CompanyAnalysisResponse):
        supported = narrative.positive_drivers if scenario == "bull" else narrative.risks

    points = [
        ScenarioPoint(
            title=claim.title,
            detail=claim.detail,
            provenance=DataProvenance(kind="live", label="Evidence-backed interpretation"),
            source_ids=claim.source_ids,
        )
        for claim in supported[:4]
    ]
    for item in demo[f"{scenario}_case"]:
        if len(points) >= 4:
            break
        points.append(ScenarioPoint(
            title=item["title"],
            detail=item["detail"],
            provenance=DataProvenance(kind="illustrative", label="Scenario illustration"),
        ))
    return ScenarioCardsBlock(
        type="scenario_cards",
        scenario=scenario,
        title="Bull case scenario" if scenario == "bull" else "Bear case scenario",
        points=points[:4],
    )


def _timeline(response: Any, company: Company) -> NewsTimelineBlock | None:
    articles = [article for article in getattr(response, "news_articles", []) if not article.company_tickers or company.ticker in article.company_tickers]
    if not articles:
        return None
    items = [TimelineItem(
        title=article.title,
        detail=article.snippet or f"Coverage from {article.source or 'source not identified'}.",
        date=article.published_at,
        url=article.url,
        provenance=DataProvenance(kind="live", label="Retrieved item", as_of=article.published_at),
    ) for article in articles[:5]]
    return NewsTimelineBlock(type="news_timeline", title="Recent coverage", items=items)


def compose_visual_response(
    response: Any,
    companies: list[Company],
    selected_components: list[str],
    generated_by: str,
) -> VisualResearchResponse:
    summary = _narrative_summary(response)
    blocks: list[Any] = []
    if response.template == "company_analysis":
        defaults = _COMPANY_DEFAULT
    elif response.template == "stock_comparison":
        # The comparison table already contains the shared metrics and fundamentals.
        # Add one chart per company while keeping large comparisons compact.
        defaults = ["comparison_table", "price_chart", "takeaways"]
    elif response.template == "technical_analysis":
        defaults = ["company_header", "metric_grid", "price_chart", "takeaways"] if len(companies) <= 5 else ["metric_grid", "price_chart"]
    elif response.template == "news_analysis":
        defaults = ["company_header", "news_timeline", "takeaways"]
    else:
        defaults = ["answer_card"] if not companies else ["company_header", "metric_grid", "takeaways"]
    requested = [component for component in selected_components if component in defaults]
    component_order = list(dict.fromkeys([*requested, *defaults]))
    allowed = set(component_order)

    if companies:
        rendered_companies = companies[:1] if response.template == "company_analysis" else companies
        demos = {company.ticker: synthetic_dataset(company.ticker) for company in rendered_companies}
        snapshots = {snapshot.ticker: snapshot for snapshot in (
            [response.market_snapshot] if isinstance(response, CompanyAnalysisResponse) and response.market_snapshot else
            getattr(response, "market_snapshots", [])
        )}
        company_for_header = response.company if isinstance(response, CompanyAnalysisResponse) else response.companies[0]
        if "company_header" in allowed:
            has_research_source = any(source.id.startswith("SRC-") for source in response.sources)
            header_provenance = DataProvenance(
                kind="live" if has_research_source else "illustrative",
                label="Research summary" if has_research_source else "Company overview",
            )
            blocks.append(CompanyHeaderBlock(
                type="company_header", company=_company_identity(company_for_header),
                description=summary or "Company overview.", provenance=header_provenance,
            ))
        for company in rendered_companies:
            snapshot = snapshots.get(company.ticker)
            metrics, points, provenance = _snapshot_metrics(snapshot, demos[company.ticker])
            display_metrics = [VisualMetric(label=_MARKET_LABELS[metric.key], value=_format_metric(metric)) for metric in metrics]
            if "metric_grid" in allowed:
                blocks.append(MetricGridBlock(type="metric_grid", title=f"Market snapshot · {company.ticker}", metrics=display_metrics, provenance=provenance))
            if "price_chart" in allowed:
                blocks.append(PriceChartBlock(type="price_chart", title=f"Price history · {company.ticker}", points=points, provenance=provenance))
            if "fundamental_cards" in allowed:
                blocks.append(FundamentalCardsBlock(
                    type="fundamental_cards", title=f"Fundamental snapshot · {company.ticker}",
                    metrics=[FundamentalMetric(**item) for item in demos[company.ticker]["fundamentals"]],
                    provenance=DataProvenance(kind="illustrative", label="Fundamental sample"),
                ))
            if "news_timeline" in allowed and isinstance(response, (CompanyAnalysisResponse, StockComparisonResponse, NewsAnalysisResponse)):
                timeline = _timeline(response, company)
                if timeline:
                    blocks.append(timeline)

        if "comparison_table" in allowed and len(companies) > 1:
            rows: list[ComparisonRow] = []
            for company in companies:
                snapshot = snapshots.get(company.ticker)
                metrics, _points, _origin = _snapshot_metrics(snapshot, demos[company.ticker])
                values = {metric.key: _format_metric(metric) for metric in metrics}
                fundamentals = demos[company.ticker]["fundamentals"]
                rows.append(ComparisonRow(
                    ticker=company.ticker, name=company.name,
                    latest_close=values.get("latest_close", "Unavailable"),
                    daily_change=values.get("daily_pct_change", "Unavailable"),
                    period_return=values.get("return_20d", "Unavailable"),
                    revenue_growth=str(fundamentals[0]["detail"]).split(" · ")[-1],
                    margin=str(fundamentals[2]["value"]),
                ))
            blocks.append(ComparisonTableBlock(
                type="comparison_table", title="Company comparison", rows=rows,
                provenance=DataProvenance(kind="mixed", label="Comparison data"),
            ))

        if "scenario_cards" in allowed and response.template == "company_analysis":
            blocks.append(_scenario_block(response, companies, "bull"))
            blocks.append(_scenario_block(response, companies, "bear"))
        if "takeaways" in allowed:
            blocks.append(TakeawaysBlock(type="takeaways", title="Takeaways", items=[summary] if summary else []))
    elif summary:
        blocks.append(AnswerCardBlock(type="answer_card", title="Answer", body=summary))

    component_rank = {component: index for index, component in enumerate(component_order)}
    blocks.sort(key=lambda block: component_rank.get(block.type, len(component_rank)))
    # Keep the response within its public schema budget even if a future template
    # adds per-company components without updating the layout policy above.
    blocks = blocks[:12]
    return VisualResearchResponse(
        template=response.template,
        title=response.title,
        summary=summary,
        blocks=blocks,
        sources=response.sources,
        unresolved_company_query=getattr(response, "unresolved_company_query", None),
        company_suggestions=getattr(response, "company_suggestions", []),
        generated_by=generated_by,  # type: ignore[arg-type]
    )
