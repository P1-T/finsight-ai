from __future__ import annotations

import re
from typing import Any

from app.api.schemas import (
    AnswerCardBlock,
    CompanyAnalysisResponse,
    CompanyHeaderBlock,
    CompanyIdentity,
    ComparisonRow,
    ComparisonTableBlock,
    DataChartBlock,
    DataChartDatum,
    DataProvenance,
    FactGridBlock,
    FactGridMetric,
    FundamentalCardsBlock,
    FundamentalMetric,
    MarketMetric,
    MetricGridBlock,
    NewsAnalysisResponse,
    NewsTimelineBlock,
    PriceChartBlock,
    PricePoint,
    QuarterlyPerformanceResponse,
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
    "scenario_cards", "news_timeline", "data_chart",
]
_FOCUSED_TEMPLATES = {
    "valuation_analysis", "dividend_analysis", "risk_analysis", "sector_analysis",
    "forward_outlook", "earnings_preview", "revenue_analysis", "growth_analysis",
    "profitability_analysis", "cash_flow_analysis", "balance_sheet_analysis", "valuation_comparison",
    "price_momentum", "trend_analysis", "support_resistance", "volume_analysis", "market_reaction",
    "catalyst_analysis", "analyst_sentiment", "insider_activity", "institutional_ownership",
    "short_interest", "options_activity", "macro_sensitivity",
}


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


def _fundamental_metrics_chart(demo: dict[str, Any], ticker: str) -> DataChartBlock:
    data: list[DataChartDatum] = []
    for metric in demo["fundamentals"]:
        value = metric["value"]
        detail = metric["detail"]
        match = re.search(r"[-+]?\d+(?:\.\d+)?%", value)
        if not match and "growth" in detail.casefold():
            match = re.search(r"[-+]?\d+(?:\.\d+)?%", detail)
        if match:
            data.append(DataChartDatum(label=metric["label"], value=float(match.group(0).rstrip("%"))))
    if len(data) < 2:
        for metric in demo["fundamentals"]:
            if metric["label"] in {"Gross margin", "Operating margin", "Free cash flow margin"}:
                match = re.search(r"[-+]?\d+(?:\.\d+)?%", metric["value"])
                if match:
                    data.append(DataChartDatum(label=metric["label"], value=float(match.group(0).rstrip("%"))))
            if len(data) >= 2:
                break
    return DataChartBlock(
        type="data_chart", chart_type="bar", title=f"Business metrics · {ticker}", unit="percent",
        data=data[:8], provenance=DataProvenance(kind="illustrative", label="Business metrics"),
    )


def _price_trend_chart(
    points: list[PricePoint], ticker: str, provenance: DataProvenance | None = None,
) -> DataChartBlock | None:
    if len(points) < 2:
        return None
    stride = max(1, len(points) // 10)
    sampled = points[::stride]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return DataChartBlock(
        type="data_chart", chart_type="line", title=f"Price trend · {ticker}", unit="USD",
        data=[DataChartDatum(label=point.date, value=point.close) for point in sampled[-12:]],
        provenance=provenance or DataProvenance(kind="illustrative", label="Price history"),
    )


def _segment_mix_chart(demo: dict[str, Any], ticker: str) -> DataChartBlock:
    return DataChartBlock(
        type="data_chart", chart_type="donut", title=f"Business mix · {ticker}", unit="percent",
        data=[DataChartDatum(label=label, value=value) for label, value in demo["segment_mix"]],
        provenance=DataProvenance(kind="illustrative", label="Business mix"),
    )


def _cash_debt_chart(demo: dict[str, Any], ticker: str) -> DataChartBlock:
    values: list[DataChartDatum] = []
    for label in ("Cash", "Debt"):
        metric = next((item for item in demo["fundamentals"] if item["label"] == label), None)
        match = re.search(r"[-+]?\d+(?:\.\d+)?", metric["value"]) if metric else None
        if match:
            values.append(DataChartDatum(label=label, value=float(match.group(0))))
    return DataChartBlock(
        type="data_chart", chart_type="bar", title=f"Cash and debt · {ticker}", unit="USD_billions",
        data=values if len(values) >= 2 else [DataChartDatum(label="Cash", value=1), DataChartDatum(label="Debt", value=1)],
        provenance=DataProvenance(kind="illustrative", label="Balance sheet sample"),
    )


def _market_breadth_chart() -> DataChartBlock:
    return DataChartBlock(
        type="data_chart", chart_type="bar", title="Market breadth", unit="percent",
        data=[DataChartDatum(label=label, value=value) for label, value in (("Large-cap", 1.8), ("Mid-cap", 0.9), ("Small-cap", -0.4))],
        provenance=DataProvenance(kind="illustrative", label="Market breadth example"),
    )


def _generic_chart(prompt: str, preferred_types: list[str]) -> DataChartBlock:
    normalized = prompt.casefold()
    preferred = preferred_types[0] if preferred_types else None
    if preferred == "line" or (preferred is None and any(word in normalized for word in ("growth", "compound", "over time", "trend"))):
        return DataChartBlock(
            type="data_chart", chart_type="line", title="Growth over time", unit="percent",
            data=[DataChartDatum(label=label, value=value) for label, value in (("Period 1", 4), ("Period 2", 9), ("Period 3", 15), ("Period 4", 23))],
            provenance=DataProvenance(kind="illustrative", label="Example trend"),
        )
    if preferred == "donut" or (preferred is None and any(word in normalized for word in ("allocation", "budget", "cash flow", "expense", "spend"))):
        return DataChartBlock(
            type="data_chart", chart_type="donut", title="Capital allocation", unit="percent",
            data=[DataChartDatum(label=label, value=value) for label, value in (("Operations", 42), ("Research", 24), ("Reinvestment", 21), ("Returns", 13))],
            provenance=DataProvenance(kind="illustrative", label="Example allocation"),
        )
    return DataChartBlock(
        type="data_chart", chart_type="bar", title="Revenue and operating profile", unit="USD_billions",
        data=[DataChartDatum(label=label, value=value) for label, value in (("Revenue", 100), ("Operating costs", 72), ("Operating income", 28))],
        provenance=DataProvenance(kind="illustrative", label="Example financial profile"),
    )


def _chart_from_pairs(
    chart_type: str,
    title: str,
    unit: str,
    pairs: list[tuple[str, float]],
    provenance: DataProvenance | None = None,
) -> DataChartBlock:
    return DataChartBlock(
        type="data_chart",
        chart_type=chart_type,  # type: ignore[arg-type]
        title=title,
        unit=unit,  # type: ignore[arg-type]
        data=[DataChartDatum(label=label, value=float(value)) for label, value in pairs[:12]],
        provenance=provenance or DataProvenance(kind="illustrative", label=title),
    )


def _analysis_chart_candidates(
    template: str,
    demo: dict[str, Any],
    ticker: str,
    points: list[PricePoint],
    provenance: DataProvenance,
    response: Any,
    companies: list[Company],
    snapshots: dict[str, Any],
) -> list[DataChartBlock]:
    metrics = demo["chart_metrics"]
    trends = demo["trend_series"]
    if template in {"valuation_analysis", "valuation_comparison"}:
        valuation_values = [
            (item["label"], float(item["value"].removesuffix("x")))
            for item in demo["valuation_analysis"]
            if item["value"].endswith("x")
        ]
        return [
            _chart_from_pairs("bar", f"Valuation multiples · {ticker}", "count", valuation_values),
            _chart_from_pairs("line", "P/E trend", "count", [(f"Period {index + 1}", value) for index, value in enumerate(trends["valuation"])]),
            _segment_mix_chart(demo, ticker),
        ]
    if template == "dividend_analysis":
        dividend = metrics["dividend"]
        return [
            _chart_from_pairs("bar", f"Dividend profile · {ticker}", "percent", [("Yield", dividend["yield"]), ("Payout ratio", dividend["payout"]), ("Dividend growth", dividend["growth"])]),
            _chart_from_pairs("line", "Dividend yield trend", "percent", [(f"Year {index + 1}", value) for index, value in enumerate(trends["dividend"])]),
            _chart_from_pairs("donut", "Earnings distribution", "percent", [("Dividend payout", dividend["payout"]), ("Retained earnings", max(1, 100 - dividend["payout"]))]),
        ]
    if template == "risk_analysis":
        risk = metrics["risk"]
        return [
            _chart_from_pairs("bar", f"Risk measures · {ticker}", "percent", [("Annualized volatility", risk["volatility"]), ("Maximum drawdown", abs(risk["drawdown"]))]),
            _chart_from_pairs("line", "Drawdown path", "percent", [(f"Period {index + 1}", value) for index, value in enumerate(trends["risk"])]),
            _chart_from_pairs("donut", "Risk factor mix", "percent", [("Market sensitivity", 38), ("Business exposure", 34), ("Liquidity and execution", 28)]),
        ]
    if template == "sector_analysis":
        sector = metrics["sector"]
        return [
            _chart_from_pairs("bar", f"Industry benchmarks · {ticker}", "percent", [("Industry growth", sector["growth"]), ("Peer median margin", sector["margin"])]),
            _chart_from_pairs("line", "Industry demand index", "count", [(f"Period {index + 1}", value) for index, value in enumerate(trends["sector"])]),
            _segment_mix_chart(demo, ticker),
        ]
    if template in {"forward_outlook", "earnings_preview"}:
        growth_text = demo["fundamentals"][0]["detail"]
        growth_match = re.search(r"[-+]?\d+(?:\.\d+)?", growth_text)
        growth = float(growth_match.group(0)) if growth_match else 0.0
        return [
            _chart_from_pairs("bar", f"Operating context · {ticker}", "percent", [
                ("Revenue growth", growth),
                ("Gross margin", float(demo["fundamentals"][1]["value"].rstrip("%"))),
                ("Operating margin", float(demo["fundamentals"][2]["value"].rstrip("%"))),
            ]),
            _chart_from_pairs("line", "Demand trend context", "count", [(f"Period {index + 1}", value) for index, value in enumerate(trends["sector"])]),
            _segment_mix_chart(demo, ticker),
        ]
    if template in {"revenue_analysis", "growth_analysis"}:
        growth_text = demo["fundamentals"][0]["detail"]
        growth_match = re.search(r"[-+]?\d+(?:\.\d+)?", growth_text)
        growth = float(growth_match.group(0)) if growth_match else 0.0
        return [
            _chart_from_pairs("bar", f"Revenue and growth · {ticker}", "percent", [("Annual growth", growth), ("Gross margin", float(demo["fundamentals"][1]["value"].rstrip("%")))]),
            _chart_from_pairs("line", "Growth trend context", "percent", [(f"Period {index + 1}", value * growth / 100) for index, value in enumerate((0.72, 0.84, 0.93, 1.02, 1.0))]),
            _segment_mix_chart(demo, ticker),
        ]
    if template == "profitability_analysis":
        margins = [(item["label"], float(item["value"].rstrip("%"))) for item in demo["fundamentals"] if item["label"] in {"Gross margin", "Operating margin", "Free cash flow margin"}]
        return [
            _chart_from_pairs("bar", f"Profitability margins · {ticker}", "percent", margins),
            _chart_from_pairs("line", "Margin trend context", "percent", [(f"Period {index + 1}", value) for index, value in enumerate((margins[0][1] * .94, margins[0][1] * .97, margins[0][1], margins[0][1] * 1.02))]),
            _chart_from_pairs("donut", "Revenue and operating costs", "percent", [("Operating income", max(1, margins[1][1])), ("Other costs", max(1, 100 - margins[1][1]))]),
        ]
    if template in {"cash_flow_analysis", "balance_sheet_analysis"}:
        cash_debt = _cash_debt_chart(demo, ticker)
        cash_debt = cash_debt.model_copy(update={
            "title": "Cash and debt profile" if template == "balance_sheet_analysis" else "Cash-generation context",
        })
        return [
            cash_debt,
            _chart_from_pairs("line", "Cash-flow trend context", "percent", [(f"Period {index + 1}", value) for index, value in enumerate(trends["dividend"])]),
            _chart_from_pairs("donut", "Cash and debt mix", "USD_billions", [("Cash", float(demo["fundamentals"][4]["value"].replace("$", "").rstrip("B"))), ("Debt", float(demo["fundamentals"][5]["value"].replace("$", "").rstrip("B")))]),
        ]
    if template in {"price_momentum", "trend_analysis", "support_resistance", "volume_analysis"}:
        computed = compute_metrics(demo["frame"])
        returns = []
        for key, label in (("return_5d", "5 sessions"), ("return_20d", "20 sessions"), ("daily_pct_change", "Latest session")):
            raw = computed[key]
            value = raw.value if hasattr(raw, "value") else raw
            if value is not None:
                returns.append((label, float(value)))
        if template == "support_resistance" and points:
            closes = [point.close for point in points]
            support, resistance = min(closes), max(closes)
            price_chart = _chart_from_pairs("bar", f"Historical price range · {ticker}", "USD", [("Support area", support), ("Latest", closes[-1]), ("Resistance area", resistance)])
        elif template == "volume_analysis":
            volumes = demo["frame"]["Volume"].tail(8).tolist()
            price_chart = _chart_from_pairs("bar", f"Recent trading volume · {ticker}", "count", [(f"Session {index + 1}", float(value)) for index, value in enumerate(volumes)])
        else:
            price_chart = _price_trend_chart(points, ticker, provenance)
        return [
            price_chart or _price_trend_chart(points, ticker, provenance),
            _chart_from_pairs("bar", f"Recent returns · {ticker}", "percent", returns),
            _chart_from_pairs("donut", "Moving-average context", "percent", [("Above reference", 58), ("Below reference", 42)]),
        ]
    if template in {"market_reaction", "catalyst_analysis", "analyst_sentiment", "insider_activity", "institutional_ownership", "short_interest", "options_activity", "macro_sensitivity"}:
        chart_titles = {
            "market_reaction": ("Price response context", "Recent move by period", "Positive and negative drivers"),
            "catalyst_analysis": ("Catalyst watchlist", "Event timeline context", "Potential impact mix"),
            "analyst_sentiment": ("Analyst view distribution", "Estimate revision trend", "Rating mix"),
            "insider_activity": ("Reported activity context", "Transaction trend", "Purchase and sale mix"),
            "institutional_ownership": ("Institutional holdings context", "Ownership trend", "Holder mix"),
            "short_interest": ("Short-interest context", "Reported short trend", "Short versus float"),
            "options_activity": ("Options activity context", "Options volume trend", "Put and call mix"),
            "macro_sensitivity": ("Macro exposure context", "Sensitivity trend", "Exposure mix"),
        }
        first_title, line_title, donut_title = chart_titles[template]
        chart_values = {
            "market_reaction": ([ ("Positive", 56), ("Neutral", 27), ("Negative", 17) ], [("Company news", 48), ("Market trend", 32), ("Other", 20)]),
            "catalyst_analysis": ([ ("Growth catalysts", 46), ("Execution risks", 34), ("External factors", 20) ], [("Earnings", 42), ("Product events", 33), ("Other", 25)]),
            "analyst_sentiment": ([ ("Buy", 61), ("Hold", 27), ("Sell", 12) ], [("Positive revisions", 45), ("Unchanged", 35), ("Negative revisions", 20)]),
            "insider_activity": ([ ("Open-market buys", 38), ("Open-market sales", 42), ("Other filings", 20) ], [("Purchases", 34), ("Sales", 46), ("Other", 20)]),
            "institutional_ownership": ([ ("Top holders", 42), ("Other institutions", 38), ("Public float", 20) ], [("Increased", 39), ("Unchanged", 37), ("Reduced", 24)]),
            "short_interest": ([ ("Short float", 18), ("Available float", 82) ], [("Prior period", 16), ("Earlier", 17), ("Recent", 18)]),
            "options_activity": ([ ("Calls", 54), ("Puts", 39), ("Other", 7) ], [("Near-term", 42), ("Mid-term", 35), ("Longer-dated", 23)]),
            "macro_sensitivity": ([ ("Interest rates", 36), ("Consumer demand", 34), ("Currency", 30) ], [("Rates", 38), ("Economic growth", 35), ("FX", 27)]),
        }
        bar_values, donut_values = chart_values[template]
        return [
            _chart_from_pairs("bar", first_title, "percent", bar_values),
            _chart_from_pairs("line", line_title, "count", [(f"Period {index + 1}", value) for index, value in enumerate((4, 6, 5, 8, 7))]),
            _chart_from_pairs("donut", donut_title, "percent", donut_values),
        ]
    if template == "company_analysis":
        return [
            _fundamental_metrics_chart(demo, ticker),
            _segment_mix_chart(demo, ticker),
            _price_trend_chart(points, ticker, provenance),
        ]
    if template == "news_analysis":
        insights = {"Positive": 0, "Neutral": 0, "Negative": 0, "Mixed": 0}
        for insight in getattr(response.narrative, "company_sentiment", []):
            insights[insight.sentiment.title()] += 1
        if not any(insights.values()):
            insights = {"Positive": 3, "Neutral": 2, "Negative": 1}
        elif sum(value > 0 for value in insights.values()) == 1:
            insights["Other"] = 1
        article_count = len(getattr(response, "news_articles", []))
        volume = [max(1, article_count - 3), max(1, article_count - 2), max(1, article_count - 1), max(1, article_count)]
        return [
            _chart_from_pairs("donut", f"Coverage sentiment · {ticker}", "count", list(insights.items())),
            _chart_from_pairs("bar", "Coverage tone counts", "count", list(insights.items())),
            _chart_from_pairs("line", "Recent coverage volume", "count", [(f"Week {index + 1}", value) for index, value in enumerate(volume)]),
        ]
    if template == "stock_comparison":
        return_data: list[tuple[str, float]] = []
        revenue_data: list[tuple[str, float]] = []
        for company in companies[:8]:
            company_demo = synthetic_dataset(company.ticker)
            market = snapshots.get(company.ticker)
            return_metric = next((metric for metric in market.metrics if metric.key == "return_20d"), None) if market else None
            if return_metric and isinstance(return_metric.value, (int, float)):
                return_value = float(return_metric.value)
            else:
                computed = compute_metrics(company_demo["frame"])
                raw_return = computed["return_20d"]
                return_value = float(raw_return.value if hasattr(raw_return, "value") else raw_return)
            return_data.append((company.ticker, return_value))
            revenue_text = company_demo["fundamentals"][0]["value"]
            revenue_match = re.search(r"[-+]?\d+(?:\.\d+)?", revenue_text)
            if revenue_match:
                revenue_data.append((company.ticker, float(revenue_match.group(0))))
        return [
            _chart_from_pairs("bar", "20-session return comparison", "percent", return_data, DataProvenance(kind="mixed", label="Return comparison")),
            _chart_from_pairs("donut", "Revenue scale comparison · USD billions", "USD_billions", revenue_data, DataProvenance(kind="illustrative", label="Revenue comparison")),
            _price_trend_chart(points, ticker, provenance),
        ]
    if template == "technical_analysis":
        risk = metrics["risk"]
        return [
            _price_trend_chart(points, ticker, provenance),
            _chart_from_pairs("bar", f"Risk measures · {ticker}", "percent", [("Volatility", risk["volatility"]), ("Maximum drawdown", abs(risk["drawdown"]))]),
            _chart_from_pairs("donut", "Risk factor mix", "percent", [("Market sensitivity", 38), ("Business exposure", 34), ("Liquidity and execution", 28)]),
        ]
    if template == "quarterly_performance":
        return [
            _fundamental_metrics_chart(demo, ticker),
            _price_trend_chart(points, ticker, provenance),
            _segment_mix_chart(demo, ticker),
        ]
    return [
        _generic_chart("growth over time", ["line"]),
        _generic_chart("compare financial metrics", ["bar"]),
        _generic_chart("cash allocation", ["donut"]),
    ]


def _scenario_block(response: Any, companies: list[Company], scenario: str) -> ScenarioCardsBlock:
    demo = synthetic_dataset(companies[0].ticker) if companies and (
        isinstance(response, CompanyAnalysisResponse) or response.template in _FOCUSED_TEMPLATES
    ) else None
    narrative = response.narrative
    supported = []
    if isinstance(response, CompanyAnalysisResponse):
        supported = narrative.positive_drivers if scenario == "bull" else narrative.risks
    elif isinstance(response, QuarterlyPerformanceResponse):
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
    for item in (demo or {}).get(f"{scenario}_case", []):
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
    prompt: str = "",
    chart_types: list[str] | None = None,
    intent_id: str | None = None,
    intent_confidence: float | None = None,
) -> VisualResearchResponse:
    summary = _narrative_summary(response)
    blocks: list[Any] = []
    if response.template == "company_analysis":
        defaults = _COMPANY_DEFAULT
    elif response.template in _FOCUSED_TEMPLATES:
        defaults = ["company_header", "metric_grid", "fundamental_cards", "data_chart", "scenario_cards", "takeaways"]
    elif response.template == "quarterly_performance":
        defaults = ["company_header", "metric_grid", "price_chart", "fact_grid", "data_chart", "scenario_cards"]
    elif response.template == "stock_comparison":
        defaults = ["comparison_table", "price_chart", "data_chart", "takeaways"]
    elif response.template == "technical_analysis":
        defaults = ["company_header", "metric_grid", "price_chart", "data_chart", "takeaways"] if len(companies) <= 5 else ["metric_grid", "price_chart", "data_chart"]
    elif response.template == "news_analysis":
        defaults = ["company_header", "news_timeline", "data_chart", "takeaways"]
    elif response.template == "clarification":
        defaults = ["answer_card"]
    else:
        defaults = ["answer_card", "data_chart"] if not companies else ["company_header", "metric_grid", "data_chart", "takeaways"]
    requested = [component for component in selected_components if component in defaults]
    component_order = list(dict.fromkeys(requested or defaults))
    allowed = set(component_order)
    if companies:
        rendered_companies = companies[:1] if response.template in {"company_analysis", "quarterly_performance"} else companies
        demos = {company.ticker: synthetic_dataset(company.ticker) for company in rendered_companies}
        snapshots = {snapshot.ticker: snapshot for snapshot in (
            [response.market_snapshot] if isinstance(response, (CompanyAnalysisResponse, QuarterlyPerformanceResponse)) and response.market_snapshot else
            getattr(response, "market_snapshots", [])
        )}
        company_for_header = response.company if isinstance(response, (CompanyAnalysisResponse, QuarterlyPerformanceResponse)) else response.companies[0]
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
                chart_title = f"Share price context · {company.ticker}" if response.template == "quarterly_performance" else f"Price history · {company.ticker}"
                blocks.append(PriceChartBlock(type="price_chart", title=chart_title, points=points, provenance=provenance))
            if "fundamental_cards" in allowed:
                if response.template in _FOCUSED_TEMPLATES:
                    card_key = "valuation_analysis" if response.template == "valuation_comparison" else response.template
                    cards = demos[company.ticker].get(card_key, demos[company.ticker]["fundamentals"][:4])
                else:
                    cards = demos[company.ticker]["fundamentals"]
                blocks.append(FundamentalCardsBlock(
                    type="fundamental_cards", title=f"Fundamental snapshot · {company.ticker}",
                    metrics=[FundamentalMetric(**item) for item in cards],
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
        if "scenario_cards" in allowed and isinstance(response, QuarterlyPerformanceResponse):
            for scenario in ("bull", "bear"):
                claims = response.narrative.positive_drivers if scenario == "bull" else response.narrative.risks
                if claims:
                    blocks.append(_scenario_block(response, companies, scenario))
        if "scenario_cards" in allowed and response.template in _FOCUSED_TEMPLATES:
            blocks.extend(_scenario_block(response, companies, scenario) for scenario in ("bull", "bear"))
        if isinstance(response, QuarterlyPerformanceResponse):
            facts = response.narrative.reported_facts
            if "fact_grid" in allowed:
                for fact_kind, title, provenance_label in (
                    ("reported", "Reported results", "Reported figures"),
                    ("guidance", "Management outlook", "Forward guidance"),
                ):
                    selected_facts = [fact for fact in facts if fact.fact_kind == fact_kind]
                    if not selected_facts:
                        continue
                    metrics: list[FactGridMetric] = []
                    for fact in selected_facts:
                        if fact_kind == "guidance":
                            detail = fact.period
                        elif fact.comparison_value is not None and fact.comparison_label:
                            detail = f"{fact.comparison_value:+g}% {fact.comparison_label}"
                        else:
                            detail = fact.comparison_label
                        metrics.append(FactGridMetric(
                            label=fact.label,
                            value=_format_financial_fact(fact.value, fact.unit, fact.range_end),
                            detail=detail,
                            range_low=_format_financial_fact(fact.value, fact.unit) if fact.range_end is not None else None,
                            range_high=_format_financial_fact(fact.range_end, fact.unit) if fact.range_end is not None else None,
                            source_ids=fact.source_ids,
                        ))
                    blocks.append(FactGridBlock(
                        type="fact_grid", title=title, period=response.narrative.period,
                        metrics=metrics,
                        provenance=DataProvenance(kind="live", label=provenance_label),
                    ))
            if "data_chart" in allowed:
                composition_facts = [fact for fact in facts if fact.fact_kind == "reported" and fact.unit == "percent" and any(word in fact.label.casefold() for word in ("share", "mix", "segment"))]
                percentage_facts = [fact for fact in facts if fact.fact_kind == "reported" and fact.unit == "percent" and any(word in fact.label.casefold() for word in ("growth", "grew", "increase", "decline", "change", "yoy", "year over year"))]
                if len(composition_facts) >= 2 and 98 <= sum(fact.value for fact in composition_facts) <= 102:
                    selected_facts = composition_facts[:8]
                    blocks.append(DataChartBlock(
                        type="data_chart", chart_type="donut", title=f"Reported segment mix · {response.narrative.period}",
                        unit="percent",
                        data=[DataChartDatum(label=fact.label, value=fact.value, source_ids=fact.source_ids) for fact in selected_facts],
                        provenance=DataProvenance(kind="live", label="Reported figures"),
                        source_ids=list(dict.fromkeys(identifier for fact in selected_facts for identifier in fact.source_ids)),
                    ))
                elif len(percentage_facts) >= 2:
                    blocks.append(DataChartBlock(
                        type="data_chart",
                        chart_type="bar",
                        title=f"Reported growth · {response.narrative.period}",
                        unit="percent",
                        data=[DataChartDatum(label=fact.label, value=fact.value, source_ids=fact.source_ids) for fact in percentage_facts[:8]],
                        provenance=DataProvenance(kind="live", label="Reported figures"),
                        source_ids=list(dict.fromkeys(identifier for fact in percentage_facts for identifier in fact.source_ids)),
                    ))
                else:
                    grouped: dict[tuple[str, str], list[Any]] = {}
                    for fact in facts:
                        grouped.setdefault((fact.label, fact.unit), []).append(fact)
                    trend = next((values for values in grouped.values() if len({fact.period for fact in values}) >= 3), None)
                    if trend:
                        ordered = sorted(trend, key=lambda fact: fact.period)
                        blocks.append(DataChartBlock(
                            type="data_chart", chart_type="line", title=f"{ordered[0].label} by period",
                            unit=ordered[0].unit,
                            data=[DataChartDatum(label=fact.period, value=fact.value, source_ids=fact.source_ids) for fact in ordered[-8:]],
                            provenance=DataProvenance(kind="live", label="Reported figures"),
                            source_ids=list(dict.fromkeys(identifier for fact in ordered for identifier in fact.source_ids)),
                        ))
        # The model chooses a layout, while the composer guarantees a rich visual
        # floor and fills chart values from live snapshots or deterministic fixtures.
        chart_count = sum(block.type in {"price_chart", "data_chart"} for block in blocks)
        if chart_count < 4:
            selected_company = companies[0] if companies else None
            demo = synthetic_dataset(selected_company.ticker) if selected_company else None
            snapshot = snapshots.get(selected_company.ticker) if selected_company else None
            points: list[PricePoint] = []
            provenance = DataProvenance(kind="illustrative", label="Market history")
            if selected_company and demo:
                _metrics, points, provenance = _snapshot_metrics(snapshot, demo)
                candidates = [
                    chart for chart in _analysis_chart_candidates(response.template, demo, selected_company.ticker, points, provenance, response, companies, snapshots)
                    if chart is not None
                ]
                candidates.append(_cash_debt_chart(demo, selected_company.ticker))
            else:
                candidates = [
                    _generic_chart(prompt, [kind]) for kind in ("line", "bar", "donut")
                ] + [_market_breadth_chart()]
            rank = {kind: index for index, kind in enumerate(chart_types or [])}
            candidates.sort(key=lambda chart: rank.get(chart.chart_type, len(rank)))
            for chart in candidates:
                if chart_count >= 4:
                    break
                if chart is not None:
                    blocks.append(chart)
                    chart_count += 1
        if "takeaways" in allowed:
            blocks.append(TakeawaysBlock(type="takeaways", title="Takeaways", items=[summary] if summary else []))
    elif summary:
        blocks.append(AnswerCardBlock(type="answer_card", title="Answer", body=summary))

    chart_count = sum(block.type in {"price_chart", "data_chart"} for block in blocks)
    if chart_count < 4:
        for chart in [
            _generic_chart(prompt, [kind]) for kind in ("line", "bar", "donut")
        ] + [_market_breadth_chart()]:
            if chart_count >= 4:
                break
            blocks.append(chart)
            chart_count += 1

    if not blocks:
        blocks.append(AnswerCardBlock(type="answer_card", title="Answer", body=summary or "Here is a concise response to your question."))

    component_rank = {component: index for index, component in enumerate(component_order)}
    blocks.sort(key=lambda block: component_rank.get(block.type, len(component_rank)))
    # Keep the response within its public schema budget even if a future template
    # adds per-company components without dropping its required chart set.
    if len(blocks) > 12:
        charts = [block for block in blocks if block.type in {"price_chart", "data_chart"}]
        other_blocks = [block for block in blocks if block.type not in {"price_chart", "data_chart"}]
        blocks = [*other_blocks[:max(0, 12 - len(charts))], *charts[:12]]
        blocks.sort(key=lambda block: component_rank.get(block.type, len(component_rank)))
    return VisualResearchResponse(
        template=response.template,
        intent_id=intent_id,
        intent_confidence=intent_confidence,
        title=response.title,
        summary=summary,
        blocks=blocks,
        sources=response.sources,
        unresolved_company_query=getattr(response, "unresolved_company_query", None),
        company_suggestions=getattr(response, "company_suggestions", []),
        generated_by=generated_by,  # type: ignore[arg-type]
    )


def _format_financial_fact(value: float, unit: str, range_end: float | None = None) -> str:
    if unit == "percent":
        start = f"{value:+g}%"
        return f"{start}–{range_end:+g}%" if range_end is not None else start
    scales = {
        "USD_billions": "$", "EUR_billions": "€",
        "USD_millions": "$", "EUR_millions": "€",
        "USD": "$", "EUR": "€",
    }
    if unit.endswith("_billions"):
        start = f"{scales[unit]}{value:,.2f}B"
        return f"{start}–{scales[unit]}{range_end:,.2f}B" if range_end is not None else start
    if unit.endswith("_millions"):
        start = f"{scales[unit]}{value:,.1f}M"
        return f"{start}–{scales[unit]}{range_end:,.1f}M" if range_end is not None else start
    if unit in {"USD", "EUR"}:
        start = f"{scales[unit]}{value:,.2f}"
        return f"{start}–{scales[unit]}{range_end:,.2f}" if range_end is not None else start
    return f"{value:,.2f}"
