from app.api.schemas import FundamentalAnalysis, NewsAnalysis, ResearchSummary, TechnicalAnalysis


def _news_perspective(news: NewsAnalysis) -> str:
    if news.status == "failed":
        return f"News analysis was unavailable. {news.error or 'The news agent did not complete.'}"
    if news.status == "no_evidence":
        return (
            "No relevant articles were returned by the news source for the documented lookback. "
            "This is not proof that no news exists."
        )
    sentiment = news.overall_sentiment or "unspecified"
    explanation = news.investor_relevance or "No additional explanation was produced."
    return (
        f"Headline-based AI interpretation of recent coverage is {sentiment}. {explanation} "
        "This is not a forecast of stock returns."
    )


def _technical_perspective(technical: TechnicalAnalysis) -> str:
    if technical.status == "failed" and technical.latest_close.value is None:
        return (
            f"Technical analysis was unavailable. {technical.error or 'The technical agent did not complete.'}"
        )
    parts: list[str] = []
    if technical.as_of_date:
        parts.append(f"Metrics are as of {technical.as_of_date.isoformat()} (provider session date, not a live quote).")
    if technical.short_term_trend:
        parts.append(f"Short-term: {technical.short_term_trend}")
    if technical.medium_term_trend:
        parts.append(f"Medium-term: {technical.medium_term_trend}")
    if technical.momentum:
        parts.append(f"Momentum: {technical.momentum}")
    if technical.status == "failed":
        parts.append(technical.error or "AI interpretation was unavailable.")
    if not parts:
        return "Technical metrics were calculated, but no interpretation text was produced."
    return " ".join(parts)


def _fundamental_perspective(fundamental: FundamentalAnalysis) -> str:
    if fundamental.status == "failed":
        return f"Fundamental analysis was unavailable. {fundamental.error or 'The filing agent did not complete.'}"
    if fundamental.status == "no_evidence":
        return "No 10-K evidence is indexed for this company. Ingest its latest SEC filing to enable this section."
    filing = f"Latest indexed 10-K filed {fundamental.filing_date.isoformat()}" if fundamental.filing_date else "Latest indexed 10-K"
    overview = fundamental.overview or "The filing was retrieved, but no narrative interpretation was produced."
    return f"{filing}: {overview}"


def combine_summary(news: NewsAnalysis, technical: TechnicalAnalysis, fundamental: FundamentalAnalysis | None = None) -> ResearchSummary:
    fundamental = fundamental or FundamentalAnalysis(status="no_evidence", error="Fundamental analysis was not requested.")
    news_ok = news.status == "succeeded"
    tech_ok = technical.status == "succeeded"

    fundamental_ok = fundamental.status == "succeeded"

    if news_ok and tech_ok and fundamental_ok:
        agreement = (
            "All three analyses completed. Their evidence uses different time horizons, so no directional agreement is inferred. "
            f"News sentiment is {news.overall_sentiment}; technical commentary covers market history; fundamentals summarize the latest 10-K."
        )
        disagreement = (
            "Headlines, price indicators, and annual filing disclosures can differ because they measure different evidence and periods. "
            "No alignment or divergence is treated as a trading signal."
        )
        missing = " ".join(filter(None, [news.evidence_limitations, *fundamental.limitations])) or "Headlines and selected filing passages; full news articles and the full filing were not reviewed."
    else:
        missing_agents = []
        if not news_ok:
            missing_agents.append("news")
        if not tech_ok:
            missing_agents.append("technical")
        if not fundamental_ok:
            missing_agents.append("fundamental")
        incomplete = ", ".join(missing_agents)
        if news_ok or tech_ok or fundamental_ok:
            agreement = f"Agreement cannot be assessed because the {incomplete} analysis is incomplete or unavailable."
            disagreement = f"The {incomplete} perspective is missing or incomplete, so relationships among all three views cannot be judged."
        else:
            agreement = "Neither agent set produced a complete analysis, so agreement is not assessed."
            disagreement = "Divergence is not assessed because all three perspectives are incomplete."
        details = [
            news.error or news.evidence_limitations if not news_ok else news.evidence_limitations,
            technical.error if not tech_ok else None,
            fundamental.error or "10-K was not ingested." if not fundamental_ok else None,
            *fundamental.limitations,
        ]
        missing = " ".join(dict.fromkeys(part for part in details if part)) or "One or more evidence sources were incomplete."

    return ResearchSummary(
        news_perspective=_news_perspective(news),
        technical_perspective=_technical_perspective(technical),
        fundamental_perspective=_fundamental_perspective(fundamental),
        agreement=agreement,
        disagreement=disagreement,
        missing_information=missing,
    )
