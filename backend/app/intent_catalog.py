"""Compact registry of supported stock-research intents and their examples."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class IntentTemplate:
    id: str
    response_template: str
    group: str
    example_prompt: str
    phrases: tuple[str, ...]
    keywords: tuple[str, ...]


# Each record is a natural-language example plus high-signal phrase/term cues.
# Several intents deliberately share a response schema; intent_id selects the
# narrower answer instructions while response_template selects reusable blocks.
_RAW: tuple[tuple[str, str, str, str, str], ...] = (
    # Fundamental: business, competitive position, governance (1–10)
    ("company_overview", "company_analysis", "Give me an overview of [company] and its business.", "company overview|business profile|what does|how does it make money", "company|business|overview|profile"),
    ("business_model", "company_analysis", "Explain [company]'s business model and main revenue streams.", "business model|revenue streams|how it makes money", "business|model|revenue|streams"),
    ("competitive_moat", "company_analysis", "Does [company] have a durable competitive moat?", "competitive moat|durable advantage|switching costs|brand loyalty", "moat|competitive|advantage|switching|brand"),
    ("competitive_position", "sector_analysis", "How does [company] compare with its competitors?", "competitive position|competitive landscape|versus competitors", "competition|competitors|position|market"),
    ("market_share", "sector_analysis", "What is [company]'s market share and is it gaining ground?", "market share|share gains|market position", "market|share|gaining|ground"),
    ("management_quality", "company_analysis", "Assess [company]'s leadership and management execution.", "management quality|leadership execution|management track record", "management|leadership|execution|track record"),
    ("capital_allocation", "cash_flow_analysis", "How does [company] allocate capital between investment and returns?", "capital allocation|uses of capital|capital deployment", "capital|allocation|investment|returns"),
    ("customer_concentration", "risk_analysis", "How exposed is [company] to a small number of customers?", "customer concentration|key customer exposure|customer dependency", "customer|concentration|dependency|exposure"),
    ("regulatory_exposure", "risk_analysis", "What regulatory or legal risks could affect [company]?", "regulatory risk|legal exposure|antitrust|litigation", "regulatory|legal|antitrust|litigation|risk"),
    ("supply_chain_exposure", "risk_analysis", "What supply-chain risks could disrupt [company]?", "supply chain risk|supplier concentration|production constraints", "supply|chain|supplier|production|constraints"),
    # Fundamental: reported performance and profitability (11–20)
    ("revenue_growth", "revenue_analysis", "How fast is [company]'s revenue growing year over year?", "revenue growth|sales growth|top line growth", "revenue|sales|growth|year|over|year"),
    ("revenue_segments", "revenue_analysis", "Which segments contribute most to [company]'s revenue?", "segment revenue|revenue mix|business segments", "segment|revenue|mix|business"),
    ("earnings_growth", "quarterly_performance", "How are [company]'s earnings and net income growing?", "net income growth|earnings growth|bottom line", "earnings|net|income|growth|profit"),
    ("eps_trend", "quarterly_performance", "How has [company]'s earnings per share changed?", "eps growth|earnings per share trend|diluted eps", "eps|earnings|per|share|trend"),
    ("earnings_quality", "quarterly_performance", "Are [company]'s reported earnings supported by cash generation?", "earnings quality|accruals|cash conversion", "earnings|quality|accruals|cash|conversion"),
    ("gross_margin", "profitability_analysis", "Are [company]'s gross margins expanding or shrinking?", "gross margin|cost of goods|gross profitability", "gross|margin|margins|cost|goods"),
    ("operating_margin", "profitability_analysis", "What is driving [company]'s operating margin trend?", "operating margin|operating profitability|operating leverage", "operating|margin|profitability|leverage"),
    ("net_margin", "profitability_analysis", "How is [company]'s net profit margin changing?", "net margin|net profit margin|bottom line margin", "net|margin|profit|profitability"),
    ("return_on_capital", "profitability_analysis", "What are [company]'s ROE and ROIC, and what do they indicate?", "return on equity|return on invested capital|roe|roic", "roe|roic|return|equity|invested|capital"),
    ("quarterly_results", "quarterly_performance", "How did [company] perform in its most recent quarter?", "previous quarter|last quarter results|quarterly earnings|reported results", "quarter|quarterly|earnings|results|reported"),
    # Fundamental: valuation and shareholder returns (21–30)
    ("intrinsic_value", "valuation_analysis", "What is [company]'s intrinsic value based on its business?", "intrinsic value|fair value|discounted cash flow", "intrinsic|value|fair|dcf|cash|flow"),
    ("valuation_overview", "valuation_analysis", "Is [company] overvalued or undervalued on current fundamentals?", "overvalued|undervalued|fairly valued|valuation overview", "valuation|overvalued|undervalued|fair"),
    ("pe_ratio", "valuation_analysis", "What is [company]'s P/E ratio and how does it compare?", "price to earnings|p/e ratio|pe multiple", "p/e|pe|ratio|earnings|multiple"),
    ("price_sales", "valuation_analysis", "How does [company]'s price-to-sales multiple look?", "price to sales|p/s ratio|sales multiple", "price|sales|ratio|multiple"),
    ("ev_ebitda", "valuation_analysis", "What is [company]'s EV/EBITDA multiple?", "ev/ebitda|enterprise value to ebitda", "ev|ebitda|enterprise|value|multiple"),
    ("peer_valuation", "valuation_comparison", "Compare [company]'s valuation with its named peers.", "peer valuation|valuation versus peers|relative multiple", "peer|valuation|relative|multiple|compare"),
    ("historical_valuation", "valuation_analysis", "How does [company]'s valuation compare with its history?", "historical valuation|valuation history|own historical average", "historical|valuation|history|average"),
    ("growth_valuation", "valuation_analysis", "Does [company]'s valuation appear supported by its growth?", "growth adjusted valuation|growth versus valuation|peg ratio", "growth|valuation|peg|ratio"),
    ("dividend_sustainability", "dividend_analysis", "Is [company]'s dividend sustainable?", "dividend sustainability|safe dividend|payout capacity", "dividend|sustainable|sustainability|payout"),
    ("shareholder_returns", "dividend_analysis", "How much capital does [company] return through dividends and buybacks?", "shareholder returns|buybacks and dividends|capital returns", "shareholder|returns|buybacks|dividends"),
    # Fundamental: balance sheet and funding (31–40)
    ("balance_sheet", "balance_sheet_analysis", "How healthy is [company]'s balance sheet?", "balance sheet health|financial position|balance sheet analysis", "balance|sheet|health|financial|position"),
    ("debt_leverage", "balance_sheet_analysis", "What is [company]'s debt-to-equity and leverage risk?", "debt to equity|debt/equity|leverage ratio", "debt|equity|leverage|ratio"),
    ("liquidity", "balance_sheet_analysis", "Can [company] cover its near-term obligations?", "liquidity|current ratio|short term obligations", "liquidity|current|ratio|short|term|obligations"),
    ("cash_position", "balance_sheet_analysis", "How much cash does [company] have relative to debt?", "cash position|cash versus debt|net cash", "cash|position|debt|net"),
    ("free_cash_flow", "cash_flow_analysis", "How strong is [company]'s free cash flow?", "free cash flow|fcf margin|cash generation", "free|cash|flow|fcf|generation"),
    ("working_capital", "balance_sheet_analysis", "Is [company]'s working capital improving?", "working capital|receivables|inventory turnover", "working|capital|receivables|inventory|turnover"),
    ("capex_investment", "cash_flow_analysis", "How are [company]'s capital expenditures changing?", "capital expenditure|capex|investment needs", "capex|capital|expenditure|investment"),
    ("dilution_buybacks", "cash_flow_analysis", "Are buybacks offsetting share dilution at [company]?", "share dilution|share repurchases|buybacks", "dilution|shares|repurchases|buybacks"),
    ("dividend_yield", "dividend_analysis", "What is [company]'s dividend yield and payout ratio?", "dividend yield|payout ratio|dividend growth", "dividend|yield|payout|ratio"),
    ("earnings_preview", "earnings_preview", "What should I watch in [company]'s upcoming earnings?", "earnings preview|upcoming earnings|earnings expectations", "earnings|preview|upcoming|expectations"),
    # Technical: price, direction, averages, oscillators (41–50)
    ("current_price", "technical_analysis", "What is [company]'s latest closing price?", "current stock price|latest close|share price today", "current|price|latest|close|share"),
    ("price_performance", "technical_analysis", "How has [company]'s stock performed over the past month?", "stock performance|price return|performance over time", "stock|performance|price|return|month"),
    ("primary_trend", "trend_analysis", "Is [company] in an uptrend, downtrend, or range?", "primary trend|uptrend|downtrend|trend direction", "trend|uptrend|downtrend|direction"),
    ("consolidation", "trend_analysis", "Is [company]'s stock consolidating or breaking out of a range?", "sideways consolidation|trading range|consolidation pattern", "sideways|consolidation|range|trading"),
    ("moving_averages", "price_momentum", "What do [company]'s 20-day and 50-day moving averages indicate?", "moving averages|20 day moving average|50 day moving average", "moving|average|20-day|50-day|sma"),
    ("long_term_average", "price_momentum", "Where is [company] relative to its 200-day moving average?", "200 day moving average|long term average|200dma", "200-day|200dma|moving|average|long-term"),
    ("average_crossover", "price_momentum", "Has [company] had a golden cross or death cross?", "golden cross|death cross|moving average crossover", "golden|death|cross|crossover|moving|average"),
    ("rsi_momentum", "price_momentum", "Is [company]'s RSI overbought or oversold?", "relative strength index|rsi|overbought|oversold", "rsi|relative|strength|index|overbought|oversold"),
    ("macd_signal", "price_momentum", "What is the MACD signal for [company]?", "macd|macd crossover|moving average convergence divergence", "macd|convergence|divergence|signal"),
    ("support_resistance", "support_resistance", "Where are the key support and resistance areas for [company]?", "support and resistance|support level|resistance level", "support|resistance|level|levels"),
    # Technical: patterns, volume, risk, relative performance (51–65)
    ("chart_patterns", "technical_analysis", "Does [company]'s chart show a recognizable pattern?", "head and shoulders|double top|double bottom|triangle pattern|chart pattern", "head|shoulders|double|top|bottom|triangle|pattern|chart"),
    ("volume_confirmation", "volume_analysis", "Is volume confirming [company]'s recent price move?", "volume confirmation|volume confirms|volume spike", "volume|confirm|price|move|spike"),
    ("breakout", "volume_analysis", "Has [company] broken out above resistance on strong volume?", "breakout|break out|break above resistance", "breakout|break|above|resistance|volume"),
    ("breakdown", "volume_analysis", "Has [company] broken below support on strong volume?", "breakdown|break below support|support failure", "breakdown|break|below|support|volume"),
    ("price_gaps", "technical_analysis", "What caused the latest gap up or gap down in [company]?", "gap up|gap down|price gap|opening gap", "gap|opening|price|up|down"),
    ("realized_volatility", "risk_analysis", "How volatile has [company]'s stock been recently?", "historical volatility|realized volatility|price volatility", "historical|realized|volatility|price"),
    ("maximum_drawdown", "risk_analysis", "What is [company]'s recent maximum drawdown?", "maximum drawdown|max drawdown|peak to trough", "maximum|drawdown|peak|trough"),
    ("market_beta", "risk_analysis", "How sensitive is [company] to broad market moves?", "beta|market sensitivity|systematic risk", "beta|market|sensitivity|systematic|risk"),
    ("relative_strength", "price_momentum", "Is [company] outperforming or underperforming the market?", "relative strength|outperforming|underperforming", "relative|strength|outperforming|underperforming|market"),
    ("company_comparison", "stock_comparison", "Compare [company] with another company or a market benchmark.", "compare stocks|compare companies|stock comparison|versus s&p 500|benchmark comparison|index performance|versus|vs.", "compare|comparison|versus|vs|stocks|companies|benchmark|index|performance"),
    ("price_correlation", "technical_analysis", "How correlated is [company] with [other company] or the market?", "price correlation|correlation with|moves with", "correlation|correlated|moves|market"),
    ("trading_liquidity", "technical_analysis", "How liquid is [company]'s stock for trading?", "trading liquidity|average daily volume|bid ask spread", "trading|liquidity|daily|volume|spread"),
    ("short_interest", "short_interest", "What is the latest reported short interest in [company]?", "short interest|shares short|days to cover", "short|interest|shares|cover"),
    ("short_squeeze_risk", "short_interest", "Could [company] face a short squeeze?", "short squeeze|days to cover|short float", "short|squeeze|cover|float"),
    ("options_activity", "options_activity", "What do [company]'s options flow and put/call ratio show?", "options activity|put/call ratio|options flow", "options|put|call|flow|ratio"),
    # Macroeconomic and market-wide (66–85)
    ("market_overview", "research_answer", "What is driving the overall US stock market today?", "market overview|overall market|us stocks today", "market|overview|overall|us|stocks"),
    ("sector_performance", "sector_analysis", "How is [company] positioned in its industry, including AI infrastructure?", "sector performance|leading sectors|lagging sectors|industry analysis|ai industry|industry trends", "sector|industry|ai|infrastructure|performance|leading|lagging"),
    ("sector_rotation", "sector_analysis", "Is there evidence of a rotation between market sectors?", "sector rotation|rotation into|rotation out of", "sector|rotation|into|out"),
    ("market_breadth", "research_answer", "How broad is the current market rally or selloff?", "market breadth|advance decline|stocks advancing", "market|breadth|advance|decline|advancing"),
    ("risk_regime", "risk_analysis", "Is the market currently risk-on or risk-off?", "risk on|risk off|risk appetite|market regime", "risk-on|risk-off|appetite|regime"),
    ("institutional_flows", "research_answer", "Are institutions net buyers or sellers in US equities?", "institutional flows|net buyers|fund flows|institutional buying", "institutional|flows|buyers|sellers|fund"),
    ("fed_rate_sensitivity", "macro_sensitivity", "How could Fed policy affect [company] and its sector?", "federal reserve|fed policy|fed rate decision", "federal|reserve|fed|policy|rate"),
    ("interest_rate_impact", "macro_sensitivity", "How do rising interest rates affect [company]?", "interest rate impact|rising rates|falling rates|borrowing costs", "interest|rates|borrowing|costs|demand"),
    ("inflation_sensitivity", "macro_sensitivity", "How exposed is [company] to inflation and input costs?", "inflation sensitivity|input cost inflation|consumer inflation", "inflation|input|costs|consumer|prices"),
    ("yield_curve", "macro_sensitivity", "What does the yield curve suggest for equities?", "yield curve|inverted yield curve|treasury curve", "yield|curve|inverted|treasury"),
    ("economic_cycle", "macro_sensitivity", "Where is [company] in the economic cycle?", "economic cycle|business cycle|cyclical exposure", "economic|business|cycle|cyclical"),
    ("recession_sensitivity", "risk_analysis", "How might [company] perform in a recession?", "recession sensitivity|recession resilience|downturn", "recession|resilience|downturn|economic"),
    ("defensive_cyclical", "sector_analysis", "Is [company] defensive or cyclical?", "defensive or cyclical|cyclical stock|defensive stock", "defensive|cyclical|economic|cycle"),
    ("currency_sensitivity", "macro_sensitivity", "How could a stronger US dollar affect [company]?", "dollar strength|currency exposure|foreign exchange", "dollar|currency|foreign|exchange|fx"),
    ("commodity_exposure", "macro_sensitivity", "How sensitive is [company] to commodity prices?", "commodity exposure|oil prices|commodity costs", "commodity|oil|prices|costs|exposure"),
    ("labor_economy", "macro_sensitivity", "How do employment and wage trends affect [company]?", "employment trends|wage inflation|labor market", "employment|wage|labor|jobs|market"),
    ("geopolitical_risk", "risk_analysis", "What geopolitical risks could affect [company] or its sector?", "geopolitical risk|geopolitical tensions|country risk", "geopolitical|risk|tensions|country"),
    ("trade_policy", "risk_analysis", "How could tariffs or trade restrictions affect [company]?", "tariffs|trade restrictions|export controls", "tariffs|trade|restrictions|export|controls"),
    ("macro_scenario", "macro_sensitivity", "How might a soft landing or recession affect equities?", "soft landing|macro scenario|economic scenario", "soft|landing|macro|scenario|recession"),
    ("earnings_season", "quarterly_performance", "What are the main themes from this earnings season?", "earnings season|earnings themes|results season", "earnings|season|themes|results"),
    # Events, expectations, flows, and catalysts (86–100)
    ("latest_news", "news_analysis", "What are the latest important news items about [company]?", "latest news|recent headlines|company updates", "latest|news|headlines|updates"),
    ("catalyst_calendar", "catalyst_analysis", "What upcoming events could act as catalysts for [company]?", "upcoming catalyst|catalyst calendar|events to watch", "upcoming|catalyst|calendar|events|watch"),
    ("market_reaction", "market_reaction", "Why did [company]'s stock move after its announcement?", "why did the stock move|market reaction|shares reacted", "why|stock|move|reaction|shares"),
    ("analyst_sentiment", "analyst_sentiment", "What is the analyst consensus on [company]?", "analyst sentiment|analyst consensus|buy hold sell", "analyst|sentiment|consensus|buy|hold|sell"),
    ("estimate_revisions", "analyst_sentiment", "Have analyst estimates for [company] been revised recently?", "estimate revisions|earnings revisions|analyst upgrades", "estimate|revisions|earnings|upgrades|downgrades"),
    ("earnings_surprise", "quarterly_performance", "Did [company] beat or miss earnings expectations?", "earnings surprise|beat estimates|missed expectations", "earnings|surprise|beat|miss|estimates|expectations"),
    ("insider_transactions", "insider_activity", "Have [company] insiders bought or sold shares recently?", "insider transactions|insider buying|insider selling", "insider|transactions|buying|selling|shares"),
    ("institutional_ownership", "institutional_ownership", "Are institutions increasing or reducing ownership in [company]?", "institutional ownership|13f holdings|ownership changes", "institutional|ownership|13f|holdings|changes"),
    ("options_sentiment", "options_activity", "What does options positioning suggest about sentiment on [company]?", "options sentiment|put call positioning|options positioning", "options|sentiment|put|call|positioning"),
    ("product_launch", "catalyst_analysis", "Could [company]'s product launch change its outlook?", "product launch|new product|product adoption", "product|launch|adoption|outlook"),
    ("merger_acquisition", "news_analysis", "What is the latest on [company]'s merger or acquisition?", "merger|acquisition|takeover|deal terms", "merger|acquisition|takeover|deal"),
    ("litigation_regulation", "risk_analysis", "What is the impact of recent litigation or regulation on [company]?", "litigation impact|new regulation|regulatory change", "litigation|regulation|regulatory|impact|legal"),
    ("leadership_change", "news_analysis", "How could a CEO or leadership change affect [company]?", "ceo change|leadership change|executive departure", "ceo|leadership|executive|departure|change"),
    ("guidance_outlook", "forward_outlook", "What guidance has [company] given for the next quarter or year?", "company guidance|management outlook|forward guidance", "guidance|management|outlook|forward|next"),
    ("future_quarter_outlook", "forward_outlook", "How is [company] expected to perform in the upcoming quarter?", "upcoming quarter|next quarter outlook|expected to perform", "upcoming|quarter|expected|perform|outlook"),
)


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", value.casefold()) if len(term) > 1}


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text.casefold()) is not None


_LAYOUT_GROUPS = {
    "company_analysis": "fundamental", "revenue_analysis": "fundamental",
    "growth_analysis": "fundamental", "profitability_analysis": "fundamental",
    "cash_flow_analysis": "fundamental", "balance_sheet_analysis": "fundamental",
    "valuation_analysis": "valuation", "valuation_comparison": "valuation",
    "dividend_analysis": "shareholder_returns", "quarterly_performance": "earnings",
    "earnings_preview": "earnings", "technical_analysis": "technical",
    "price_momentum": "technical", "trend_analysis": "technical",
    "support_resistance": "technical", "volume_analysis": "technical",
    "risk_analysis": "risk", "sector_analysis": "market_context",
    "macro_sensitivity": "market_context", "research_answer": "market_context",
    "news_analysis": "news_and_events", "catalyst_analysis": "news_and_events",
    "market_reaction": "news_and_events", "analyst_sentiment": "market_sentiment",
    "insider_activity": "ownership_and_flows", "institutional_ownership": "ownership_and_flows",
    "short_interest": "ownership_and_flows", "options_activity": "derivatives",
    "stock_comparison": "comparison",
}

INTENT_TEMPLATES = tuple(
    IntentTemplate(
        id=identifier,
        response_template=response_template,
        group=_LAYOUT_GROUPS.get(response_template, "company_research"),
        example_prompt=example,
        phrases=tuple(phrase.strip().casefold() for phrase in phrases.split("|") if phrase.strip()),
        keywords=tuple(sorted(_terms(f"{keywords} {example}"))),
    )
    for identifier, response_template, example, phrases, keywords in _RAW
)
INTENT_BY_ID = {template.id: template for template in INTENT_TEMPLATES}
_DOCUMENT_FREQUENCY: dict[str, int] = {}
for _template in INTENT_TEMPLATES:
    for _word in set(_template.keywords):
        _DOCUMENT_FREQUENCY[_word] = _DOCUMENT_FREQUENCY.get(_word, 0) + 1
_GENERIC_WORDS = {
    "company", "stock", "stocks", "share", "shares", "market", "what", "how", "does",
    "could", "would", "should", "about", "recent", "latest", "based", "analysis", "analyze",
    "look", "show", "tell", "give", "me", "its", "their", "the", "and", "for", "from",
    "with", "into", "over", "under", "are", "is", "has", "have", "this", "that", "does",
    "perform", "performance",
}


@dataclass(frozen=True)
class RankedIntent:
    template: IntentTemplate
    score: float
    confidence: float
    matched_phrases: tuple[str, ...]


def rank_intents(
    prompt: str,
    limit: int = 8,
    context: str = "",
    company_count: int | None = None,
) -> list[RankedIntent]:
    """Rank the 100 catalog intents with phrase, rarity, and token-overlap scores."""
    prompt_terms = _terms(prompt) - _GENERIC_WORDS
    if not prompt_terms:
        prompt_terms = _terms(prompt)
    context_terms = _terms(context) - _GENERIC_WORDS
    ranked: list[RankedIntent] = []
    for template in INTENT_TEMPLATES:
        matched = tuple(phrase for phrase in template.phrases if _contains_phrase(prompt, phrase))
        overlap = prompt_terms.intersection(template.keywords)
        context_overlap = context_terms.intersection(template.keywords)
        rarity_score = sum(
            1.0 + math.log((len(INTENT_TEMPLATES) + 1) / (_DOCUMENT_FREQUENCY.get(word, 1) + 1))
            for word in overlap
        )
        phrase_score = max((4.0 + min(2.0, len(_terms(phrase)) * 0.3) for phrase in matched), default=0.0)
        token_score = rarity_score / max(1.0, math.sqrt(len(template.keywords))) * 3.2
        context_phrase_score = max((4.0 + min(2.0, len(_terms(phrase)) * 0.3) for phrase in template.phrases if _contains_phrase(context, phrase)), default=0.0)
        context_token_score = sum(
            1.0 + math.log((len(INTENT_TEMPLATES) + 1) / (_DOCUMENT_FREQUENCY.get(word, 1) + 1))
            for word in context_overlap
        ) / max(1.0, math.sqrt(len(template.keywords))) * 3.2
        score = phrase_score + token_score + 0.25 * (context_phrase_score + context_token_score)
        if template.response_template == "stock_comparison":
            if company_count is not None and company_count >= 2:
                score += 3.0
            elif company_count == 1 and not any(
                _contains_phrase(prompt, cue)
                for cue in ("benchmark", "s&p 500", "market index", "index performance")
            ):
                score -= 2.0
        if score <= 0:
            continue
        confidence = min(0.99, score / (score + 4.0))
        ranked.append(RankedIntent(template, score, confidence, matched))
    ranked.sort(key=lambda result: (-result.score, result.template.id))
    return ranked[: max(1, min(limit, len(INTENT_TEMPLATES)))]


def select_intent(
    prompt: str,
    llm_intent_id: str | None = None,
    context: str = "",
    company_count: int | None = None,
) -> RankedIntent:
    """Combine deterministic evidence scores with a bounded Claude preference."""
    base = rank_intents(prompt, limit=len(INTENT_TEMPLATES), context=context, company_count=company_count)
    if not base:
        if llm_intent_id in INTENT_BY_ID:
            return RankedIntent(INTENT_BY_ID[llm_intent_id], 1.6, 0.286, ())
        return RankedIntent(INTENT_BY_ID["company_overview"], 0.0, 0.0, ())
    scores = {result.template.id: result.score for result in base}
    if llm_intent_id in INTENT_BY_ID:
        # The model can refine a close semantic match; a strong exact phrase cue
        # still wins over an unrelated choice.
        scores[llm_intent_id] = scores.get(llm_intent_id, 0.0) + 1.6
    chosen_id = max(scores, key=scores.get)
    result = next((item for item in base if item.template.id == chosen_id), None)
    if result is None:
        result = RankedIntent(INTENT_BY_ID[chosen_id], scores[chosen_id], 0.0, ())
    chosen_score = scores[chosen_id]
    runner_up = max((score for identifier, score in scores.items() if identifier != chosen_id), default=0.0)
    absolute_evidence = chosen_score / (chosen_score + 4.0)
    separation = max(0.0, chosen_score - runner_up) / max(2.0, chosen_score + 2.0)
    confidence = min(0.99, 0.65 * absolute_evidence + 0.35 * separation)
    return RankedIntent(result.template, chosen_score, confidence, result.matched_phrases)


def prompt_candidates(
    prompt: str,
    limit: int = 8,
    context: str = "",
    company_count: int | None = None,
) -> list[dict[str, str | float]]:
    ranked = rank_intents(prompt, limit=limit, context=context, company_count=company_count)
    if not ranked:
        fallback = (INTENT_BY_ID["company_overview"], INTENT_BY_ID["market_overview"])
        return [
            {
                "id": template.id,
                "response_template": template.response_template,
                "group": template.group,
                "example_prompt": template.example_prompt,
                "score": 0.0,
            }
            for template in fallback
        ]
    return [
        {
            "id": result.template.id,
            "response_template": result.template.response_template,
            "group": result.template.group,
            "example_prompt": result.template.example_prompt,
            "score": round(result.score, 3),
        }
        for result in ranked
    ]

