from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.api.schemas import Ticker
from app.config import Settings, get_settings
from app.utils.errors import ProviderError

CIKS = {Ticker.AAPL: "0000320193", Ticker.NVDA: "0001045810", Ticker.MSFT: "0000789019"}
SEC_BASE = "https://www.sec.gov"
DATA_BASE = "https://data.sec.gov"
SECTION_ITEMS = [
    ("Item 1. Business", re.compile(r"\bitem\s+1\.?\s+business\b", re.I)),
    ("Item 1A. Risk Factors", re.compile(r"\bitem\s+1a\.?\s+risk\s+factors\b", re.I)),
    ("Item 7. Management’s Discussion and Analysis", re.compile(r"\bitem\s+7\.?\s+management.{0,15}discussion\b", re.I)),
    ("Item 8. Financial Statements", re.compile(r"\bitem\s+8\.?\s+financial\s+statements\b", re.I)),
]


@dataclass(frozen=True)
class Filing:
    ticker: Ticker
    accession: str
    filing_date: date
    fiscal_year: int
    url: str
    html: str
    company_facts: dict[str, Any]


def _headers(settings: Settings) -> dict[str, str]:
    user_agent = settings.sec_user_agent.strip()
    if not user_agent or "your-email@example.com" in user_agent:
        raise ProviderError("Configure SEC_USER_AGENT with a real contact email before using SEC EDGAR.")
    return {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}


def _get_json(client: httpx.Client, url: str, headers: dict[str, str]) -> dict[str, Any]:
    response = client.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ProviderError("SEC EDGAR returned an invalid JSON response.")
    return data


def fetch_latest_10k(ticker: Ticker, settings: Settings | None = None) -> Filing:
    resolved = settings or get_settings()
    headers = _headers(resolved)
    cik = CIKS[ticker]
    try:
        with httpx.Client(timeout=resolved.sec_timeout_seconds, follow_redirects=True) as client:
            submissions = _get_json(client, f"{DATA_BASE}/submissions/CIK{cik}.json", headers)
            recent = submissions.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            index = next(i for i, form in enumerate(forms) if form == "10-K")
            accession = recent["accessionNumber"][index]
            filed = date.fromisoformat(recent["filingDate"][index])
            report_dates = recent.get("reportDate", [])
            fiscal_year = int(report_dates[index][:4]) if index < len(report_dates) and report_dates[index] else filed.year
            primary = recent["primaryDocument"][index]
            accession_path = accession.replace("-", "")
            filing_url = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{accession_path}/{primary}"
            filing_response = client.get(filing_url, headers=headers)
            filing_response.raise_for_status()
            facts = _get_json(client, f"{DATA_BASE}/api/xbrl/companyfacts/CIK{cik}.json", headers)
    except (httpx.HTTPError, ValueError, KeyError, IndexError, StopIteration, TypeError) as exc:
        raise ProviderError("Could not retrieve the latest SEC 10-K filing.") from exc
    return Filing(ticker, accession, filed, fiscal_year, filing_url, filing_response.text, facts)


def extract_sections(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "ix:header", "header", "footer"]):
        node.decompose()
    lines = [re.sub(r"\s+", " ", line).strip() for line in soup.get_text("\n").splitlines()]
    lines = [line for line in lines if line]
    # 10-K tables of contents repeat the Item labels; selecting the final occurrence
    # favors the actual report body while preserving section boundaries.
    markers: list[tuple[int, str]] = []
    for title, pattern in SECTION_ITEMS:
        candidates = [i for i, line in enumerate(lines) if pattern.search(line)]
        if candidates:
            markers.append((candidates[-1], title))
    markers.sort()
    sections: dict[str, str] = {}
    for position, (start, title) in enumerate(markers):
        end = markers[position + 1][0] if position + 1 < len(markers) else len(lines)
        content = "\n".join(lines[start + 1 : end]).strip()
        if content:
            sections[title] = content
    if not sections:
        raise ProviderError("Could not identify the expected sections in the SEC 10-K HTML.")
    return sections


def _fact_values(facts: dict[str, Any], accession: str, tags: tuple[str, ...], instant: bool = False) -> tuple[float | None, str | None, int | None]:
    namespaces = facts.get("facts", {})
    for namespace in ("us-gaap", "dei"):
        entries = namespaces.get(namespace, {})
        for tag in tags:
            units = entries.get(tag, {}).get("units", {})
            for unit, rows in units.items():
                matching = [row for row in rows if row.get("accn") == accession and row.get("form") == "10-K"]
                if not instant:
                    matching = [row for row in matching if row.get("start") and 300 <= (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days <= 400]
                else:
                    matching = [row for row in matching if not row.get("start")]
                matching.sort(key=lambda row: row.get("end", ""), reverse=True)
                if matching:
                    row = matching[0]
                    return float(row["val"]), unit, date.fromisoformat(row["end"]).year
    return None, None, None


def extract_fundamental_metrics(filing: Filing) -> dict[str, dict[str, Any]]:
    facts = filing.company_facts
    acc = filing.accession
    specs = {
        "revenue": (("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"), False),
        "operating_income": (("OperatingIncomeLoss",), False),
        "net_income": (("NetIncomeLoss",), False),
        "operating_cash_flow": (("NetCashProvidedByUsedInOperatingActivities",), False),
        "capital_expenditures": (("PaymentsToAcquirePropertyPlantAndEquipment",), False),
        "cash_and_equivalents": (("CashAndCashEquivalentsAtCarryingValue",), True),
    }
    result: dict[str, dict[str, Any]] = {}
    for name, (tags, instant) in specs.items():
        value, unit, year = _fact_values(facts, acc, tags, instant)
        result[name] = {"value": value, "unit": unit, "fiscal_year": year}
    revenue, operating, net = (result[k]["value"] for k in ("revenue", "operating_income", "net_income"))
    cash_flow, capex = result["operating_cash_flow"]["value"], result["capital_expenditures"]["value"]
    # XBRL companyfacts includes comparative values under the same filing accession.
    revenue_rows = []
    for namespace in ("us-gaap",):
        for tag in specs["revenue"][0]:
            for unit_rows in facts.get("facts", {}).get(namespace, {}).get(tag, {}).get("units", {}).values():
                revenue_rows.extend(row for row in unit_rows if row.get("accn") == acc and row.get("form") == "10-K" and row.get("start") and 300 <= (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days <= 400)
    by_year = {}
    for row in revenue_rows:
        by_year.setdefault(date.fromisoformat(row["end"]).year, row["val"])
    years = sorted(by_year)
    growth = ((float(by_year[years[-1]]) / float(by_year[years[-2]]) - 1) * 100) if len(years) >= 2 and float(by_year[years[-2]]) != 0 else None
    result["revenue_yoy_growth_pct"] = {"value": growth, "unit": "percent", "fiscal_year": years[-1] if years else filing.fiscal_year}
    result["operating_margin_pct"] = {"value": operating / revenue * 100 if operating is not None and revenue else None, "unit": "percent", "fiscal_year": filing.fiscal_year}
    result["net_margin_pct"] = {"value": net / revenue * 100 if net is not None and revenue else None, "unit": "percent", "fiscal_year": filing.fiscal_year}
    result["free_cash_flow"] = {"value": cash_flow - abs(capex) if cash_flow is not None and capex is not None else None, "unit": result["operating_cash_flow"]["unit"], "fiscal_year": result["operating_cash_flow"]["fiscal_year"]}
    return result


def chunk_sections(sections: dict[str, str], max_words: int = 380, overlap_words: int = 55) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for section, body in sections.items():
        words = body.split()
        step = max_words - overlap_words
        for offset in range(0, len(words), step):
            part = " ".join(words[offset : offset + max_words]).strip()
            if part:
                chunks.append({"section": section, "text": part})
            if offset + max_words >= len(words):
                break
    return chunks
