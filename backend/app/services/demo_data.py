from __future__ import annotations

import hashlib
import json
import random
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_company_fixtures.json"

_SCENARIOS: dict[str, dict[str, list[dict[str, str]]]] = {
    "consumer_hardware": {
        "bull": [
            {"title": "Ecosystem engagement", "detail": "If customers deepen use of connected devices and services, recurring ecosystem revenue could grow."},
            {"title": "Product upgrade cycle", "detail": "A stronger replacement cycle could lift unit demand and average selling prices."},
            {"title": "Services mix", "detail": "A larger services contribution could support more resilient gross margins."},
            {"title": "Capital returns", "detail": "Sustained cash generation could preserve flexibility for investment and shareholder returns."},
        ],
        "bear": [
            {"title": "Longer replacement cycles", "detail": "Customers could keep devices longer, slowing hardware revenue growth."},
            {"title": "Market saturation", "detail": "Mature product categories could limit incremental unit growth."},
            {"title": "Supply-chain exposure", "detail": "Manufacturing concentration or component constraints could disrupt deliveries or margins."},
            {"title": "Regulatory and platform pressure", "detail": "Policy changes or platform restrictions could weigh on services economics."},
        ],
    },
    "cloud_software": {
        "bull": [
            {"title": "Cloud workload growth", "detail": "If customers move more workloads to cloud platforms, consumption and subscription revenue could expand."},
            {"title": "AI product adoption", "detail": "Paid adoption of AI tools could increase customer usage and average contract value."},
            {"title": "Recurring revenue base", "detail": "Renewals and multi-year contracts could support revenue visibility."},
            {"title": "Operating leverage", "detail": "Revenue growth outpacing operating costs could improve margins and cash generation."},
        ],
        "bear": [
            {"title": "Cloud optimization", "detail": "Customers could optimize usage or delay migrations, slowing cloud growth."},
            {"title": "AI monetization gap", "detail": "AI infrastructure spending could rise faster than paid customer adoption."},
            {"title": "Competitive pricing", "detail": "Strong competition could pressure renewal rates, pricing, or market share."},
            {"title": "Execution and security risk", "detail": "Service outages, cyber incidents, or product delays could damage customer trust."},
        ],
    },
    "semiconductors": {
        "bull": [
            {"title": "Compute demand", "detail": "Stronger data-center and accelerated-computing demand could support higher shipments."},
            {"title": "Product mix", "detail": "A richer mix of advanced products could support revenue and gross-margin growth."},
            {"title": "New platform adoption", "detail": "Successful product launches could expand the addressable market and customer commitments."},
            {"title": "Software and ecosystem", "detail": "Developer tools and platform lock-in could reinforce demand for hardware products."},
        ],
        "bear": [
            {"title": "Semiconductor cyclicality", "detail": "A pause in customer spending or inventory corrections could reduce orders."},
            {"title": "Customer concentration", "detail": "A small number of large buyers could create lumpy demand and bargaining pressure."},
            {"title": "Supply constraints", "detail": "Foundry, packaging, memory, or power constraints could limit deliveries."},
            {"title": "Export and competition risk", "detail": "Trade restrictions or competing architectures could reduce addressable demand."},
        ],
    },
    "cybersecurity": {
        "bull": [
            {"title": "Platform consolidation", "detail": "Customers could consolidate security tools onto a broader platform, increasing spend per customer."},
            {"title": "Cloud and identity security", "detail": "Broader adoption across cloud and identity workloads could expand product usage."},
            {"title": "Recurring subscriptions", "detail": "Renewals and additional modules could support recurring revenue growth."},
            {"title": "Scale efficiencies", "detail": "Revenue growth outpacing sales and infrastructure costs could improve operating leverage."},
        ],
        "bear": [
            {"title": "Trust and service risk", "detail": "A major product incident or service disruption could weaken customer confidence."},
            {"title": "Crowded security market", "detail": "Platform vendors and focused competitors could pressure pricing or retention."},
            {"title": "High growth investment", "detail": "Sales, research, and infrastructure spending could constrain margin expansion."},
            {"title": "Growth expectations", "detail": "A slowdown in customer additions or module adoption could challenge elevated expectations."},
        ],
    },
    "digital_platforms": {
        "bull": [
            {"title": "Engagement growth", "detail": "Higher user engagement could increase monetizable impressions and platform activity."},
            {"title": "Advertising demand", "detail": "Improving advertiser demand and targeting effectiveness could support revenue growth."},
            {"title": "AI-driven relevance", "detail": "Better recommendation and ad systems could improve engagement and monetization."},
            {"title": "New monetization paths", "detail": "Commerce, messaging, or subscription products could add revenue streams."},
        ],
        "bear": [
            {"title": "Advertising sensitivity", "detail": "A weaker economy could reduce marketing budgets and ad pricing."},
            {"title": "Privacy and regulation", "detail": "Policy or platform changes could limit targeting and data use."},
            {"title": "AI infrastructure costs", "detail": "Large computing investments could rise faster than monetization."},
            {"title": "User preference shifts", "detail": "Changes in user behavior could reduce engagement or platform relevance."},
        ],
    },
    "commerce_cloud": {
        "bull": [
            {"title": "Retail efficiency", "detail": "Improved fulfillment density and operations could support retail profitability."},
            {"title": "Cloud demand", "detail": "Higher enterprise cloud usage could strengthen recurring infrastructure revenue."},
            {"title": "Advertising mix", "detail": "Growth in higher-margin advertising could improve the business mix."},
            {"title": "Scale advantage", "detail": "Logistics and technology scale could support customer retention and cost efficiency."},
        ],
        "bear": [
            {"title": "Consumer demand", "detail": "Weaker discretionary spending could pressure retail volumes and mix."},
            {"title": "Cloud competition", "detail": "Price competition or slower workloads could weigh on cloud growth."},
            {"title": "Capital intensity", "detail": "Fulfillment and data-center investment could pressure free cash flow."},
            {"title": "Regulatory scrutiny", "detail": "Antitrust or labor rules could increase costs or constrain business practices."},
        ],
    },
    "mobility": {
        "bull": [
            {"title": "Vehicle platform scale", "detail": "Higher production scale could improve manufacturing efficiency."},
            {"title": "Software and services", "detail": "Software, charging, and service offerings could add higher-margin revenue."},
            {"title": "New product adoption", "detail": "Successful launches could broaden the customer base and demand profile."},
            {"title": "Cost reductions", "detail": "Lower unit costs could support margins while preserving price competitiveness."},
        ],
        "bear": [
            {"title": "Price competition", "detail": "Discounting by the company or its competitors could pressure margins."},
            {"title": "Production execution", "detail": "Factory delays or quality issues could disrupt deliveries and costs."},
            {"title": "Demand cyclicality", "detail": "High interest rates or cautious buyers could defer vehicle purchases."},
            {"title": "Technology and regulation", "detail": "Safety, autonomy, or regulatory setbacks could delay expected opportunities."},
        ],
    },
    "enterprise_software": {
        "bull": [
            {"title": "Enterprise adoption", "detail": "Broader deployment could increase recurring platform and usage revenue."},
            {"title": "AI use cases", "detail": "Successful enterprise AI deployments could expand customer budgets and workloads."},
            {"title": "Land and expand", "detail": "Existing customers could add products and use cases over time."},
            {"title": "Cash-flow scale", "detail": "A recurring software model could support cash generation as the customer base grows."},
        ],
        "bear": [
            {"title": "Long sales cycles", "detail": "Large enterprise purchases could be delayed during budget reviews."},
            {"title": "Adoption uncertainty", "detail": "Pilot projects may not convert into broad paid deployments."},
            {"title": "Competitive alternatives", "detail": "Incumbent vendors or open-source tools could constrain pricing."},
            {"title": "Growth-to-valuation risk", "detail": "Slower customer expansion could make expectations harder to sustain."},
        ],
    },
}

_DEFAULT_SCENARIOS = _SCENARIOS["enterprise_software"]


@lru_cache(maxsize=1)
def _stored_fixtures() -> dict[str, dict[str, Any]]:
    return json.loads(_DATA_PATH.read_text(encoding="utf-8"))


def synthetic_dataset(ticker: str) -> dict[str, Any]:
    """Return stable stored fixtures for popular tickers and deterministic fallback for others."""
    symbol = ticker.upper()
    seed = int.from_bytes(hashlib.sha256(symbol.encode()).digest()[:8], "big")
    rng = random.Random(seed)
    stored = _stored_fixtures().get(symbol)
    if stored:
        profile = stored["profile"]
        revenue = float(stored["revenue_bn"])
        growth = float(stored["growth_pct"])
        gross_margin = float(stored["gross_margin_pct"])
        operating_margin = float(stored["operating_margin_pct"])
        fcf_margin = float(stored["fcf_margin_pct"])
        cash = float(stored["cash_bn"])
        debt = float(stored["debt_bn"])
        start_price = float(stored["price_start"])
        end_price = float(stored["price_end"])
    else:
        profile = "enterprise_software"
        revenue = round(rng.uniform(1.2, 86.0), 1)
        growth = round(rng.uniform(-8.0, 34.0), 1)
        gross_margin = round(rng.uniform(28.0, 82.0), 1)
        operating_margin = round(gross_margin * rng.uniform(0.18, 0.62), 1)
        fcf_margin = round(rng.uniform(4.0, 31.0), 1)
        cash = round(revenue * rng.uniform(0.08, 0.55), 1)
        debt = round(revenue * rng.uniform(0.03, 0.42), 1)
        start_price = rng.uniform(45, 420)
        end_price = start_price * rng.uniform(0.8, 1.35)

    today = datetime.now(timezone.utc).date()
    sessions: list[date] = []
    cursor = today
    while len(sessions) < 126:
        if cursor.weekday() < 5:
            sessions.append(cursor)
        cursor -= timedelta(days=1)
    sessions.reverse()

    closes: list[float] = []
    for index in range(len(sessions)):
        progress = index / (len(sessions) - 1)
        baseline = start_price + (end_price - start_price) * progress
        wave = 1 + 0.035 * (progress * 4 - 2) * (progress - 0.5)
        jitter = 1 + rng.gauss(0, 0.012)
        closes.append(round(max(2.0, baseline * wave * jitter), 2))
    closes[0], closes[-1] = round(start_price, 2), round(end_price, 2)
    volumes = [rng.randint(800_000, 25_000_000) for _ in sessions]
    frame = pd.DataFrame({"Close": closes, "Volume": volumes}, index=pd.to_datetime(sessions, utc=True))
    fundamentals = [
        {"label": "Revenue", "value": f"${revenue:.1f}B", "detail": f"Annual revenue · {growth:+.1f}% growth"},
        {"label": "Gross margin", "value": f"{gross_margin:.1f}%", "detail": "Gross profit as a share of revenue"},
        {"label": "Operating margin", "value": f"{operating_margin:.1f}%", "detail": "Operating income as a share of revenue"},
        {"label": "Free cash flow margin", "value": f"{fcf_margin:.1f}%", "detail": "Free cash flow as a share of revenue"},
        {"label": "Cash", "value": f"${cash:.1f}B", "detail": "Cash and equivalents"},
        {"label": "Debt", "value": f"${debt:.1f}B", "detail": "Total debt"},
    ]
    scenarios = _SCENARIOS.get(profile, _DEFAULT_SCENARIOS)
    segment_mix_by_profile = {
        "consumer_hardware": [("Devices", 58), ("Services", 27), ("Wearables", 9), ("Other", 6)],
        "cloud_software": [("Cloud", 54), ("Software", 25), ("Services", 14), ("Other", 7)],
        "semiconductors": [("Data center", 46), ("Client", 27), ("Networking", 16), ("Other", 11)],
        "cybersecurity": [("Platform", 52), ("Subscriptions", 28), ("Services", 13), ("Other", 7)],
        "digital_platforms": [("Advertising", 76), ("Subscriptions", 13), ("Devices", 7), ("Other", 4)],
        "commerce_cloud": [("Commerce", 48), ("Cloud", 31), ("Advertising", 15), ("Other", 6)],
        "mobility": [("Vehicles", 82), ("Services", 10), ("Energy", 5), ("Other", 3)],
        "enterprise_software": [("Subscriptions", 56), ("Licenses", 22), ("Services", 16), ("Other", 6)],
    }
    pe_ratio = round(rng.uniform(14, 68), 1)
    dividend_yield = round(rng.uniform(0.1, 3.8), 2)
    valuation = [
        {"label": "Trailing P/E", "value": f"{pe_ratio:.1f}x", "detail": "Price relative to trailing earnings"},
        {"label": "Forward P/E", "value": f"{max(8, pe_ratio * rng.uniform(0.72, 1.08)):.1f}x", "detail": "Price relative to estimated earnings"},
        {"label": "Price / sales", "value": f"{rng.uniform(1.5, 28):.1f}x", "detail": "Price relative to revenue"},
        {"label": "EV / EBITDA", "value": f"{rng.uniform(7, 42):.1f}x", "detail": "Enterprise value relative to EBITDA"},
    ]
    dividend = [
        {"label": "Dividend yield", "value": f"{dividend_yield:.2f}%", "detail": "Annualized dividend relative to share price"},
        {"label": "Annual dividend", "value": f"${start_price * dividend_yield / 100:.2f}", "detail": "Per share"},
        {"label": "Payout ratio", "value": f"{rng.uniform(18, 78):.1f}%", "detail": "Dividend relative to earnings"},
        {"label": "5-year dividend growth", "value": f"{rng.uniform(0, 14):.1f}%", "detail": "Annualized growth rate"},
    ]
    risk = [
        {"label": "Beta", "value": f"{rng.uniform(0.55, 2.05):.2f}", "detail": "Sensitivity to broad-market moves"},
        {"label": "Annualized volatility", "value": f"{rng.uniform(18, 68):.1f}%", "detail": "Historical price variability"},
        {"label": "Maximum drawdown", "value": f"-{rng.uniform(12, 52):.1f}%", "detail": "Peak-to-trough decline"},
        {"label": "Downside capture", "value": f"{rng.uniform(65, 145):.1f}%", "detail": "Relative loss in declining periods"},
    ]
    sector = [
        {"label": "Industry revenue growth", "value": f"{rng.uniform(-4, 24):+.1f}%", "detail": "Current annual growth context"},
        {"label": "Peer median margin", "value": f"{rng.uniform(8, 38):.1f}%", "detail": "Operating margin benchmark"},
        {"label": "Demand index", "value": f"{rng.uniform(65, 145):.0f}", "detail": "Relative demand, indexed to 100"},
        {"label": "Competitive intensity", "value": f"{rng.uniform(35, 90):.0f}/100", "detail": "Market concentration and rivalry"},
    ]
    return {
        "frame": frame,
        "points": [{"date": session.isoformat(), "close": close} for session, close in zip(sessions, closes, strict=True)],
        "as_of": sessions[-1].isoformat(),
        "fundamentals": fundamentals,
        "segment_mix": segment_mix_by_profile.get(profile, segment_mix_by_profile["enterprise_software"]),
        "valuation_analysis": valuation,
        "dividend_analysis": dividend,
        "risk_analysis": risk,
        "sector_analysis": sector,
        "chart_metrics": {
            "valuation": {"pe": pe_ratio, "price_sales": float(valuation[2]["value"].removesuffix("x")), "ev_ebitda": float(valuation[3]["value"].removesuffix("x"))},
            "dividend": {"yield": dividend_yield, "payout": float(dividend[2]["value"].removesuffix("%")), "growth": float(dividend[3]["value"].removesuffix("%"))},
            "risk": {"beta": float(risk[0]["value"]), "volatility": float(risk[1]["value"].removesuffix("%")), "drawdown": float(risk[2]["value"].removesuffix("%"))},
            "sector": {"growth": float(sector[0]["value"].removesuffix("%")), "margin": float(sector[1]["value"].removesuffix("%")), "demand": float(sector[2]["value"])},
        },
        "trend_series": {
            "valuation": [round(pe_ratio * factor, 1) for factor in (0.78, 0.91, 1.07, 0.96, 1.0)],
            "dividend": [round(dividend_yield * factor, 2) for factor in (1.3, 1.2, 1.12, 1.06, 1.0)],
            "risk": [round(value, 1) for value in (rng.uniform(-8, -3), rng.uniform(-15, -8), rng.uniform(-24, -12), rng.uniform(-11, -4), -rng.uniform(0, 8))],
            "sector": [round(value, 1) for value in (92, 96, 101, 105, rng.uniform(103, 121))],
        },
        "bull_case": scenarios["bull"],
        "bear_case": scenarios["bear"],
        "fixture_ticker": symbol if stored else None,
    }
