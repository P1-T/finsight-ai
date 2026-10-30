from datetime import date

import pytest

from app.api.schemas import Ticker
from app.config import Settings
from app.rag.sec_edgar import (
    Filing,
    _headers,
    chunk_sections,
    extract_fundamental_metrics,
    extract_sections,
)
from app.utils.errors import ProviderError


def test_section_extraction_and_chunking() -> None:
    html = """
    <html><body>
      <div>Table of Contents</div><div>Item 1. Business</div>
      <div>Item 1A. Risk Factors</div><div>Item 7. Management Discussion</div>
      <div>Item 8. Financial Statements</div>
      <div>Item 1. Business</div><p>Company products and markets.</p>
      <div>Item 1A. Risk Factors</div><p>Competition and regulation.</p>
      <div>Item 7. Management's Discussion</div><p>Revenue increased.</p>
      <div>Item 8. Financial Statements</div><p>Cash flows and balance sheet.</p>
    </body></html>
    """
    sections = extract_sections(html)
    assert "Company products" in sections["Item 1. Business"]
    assert "Competition" in sections["Item 1A. Risk Factors"]
    chunks = chunk_sections({"Business": "word " * 800}, max_words=100, overlap_words=10)
    assert len(chunks) > 1
    assert chunks[0]["text"].split()[-10:] == chunks[1]["text"].split()[:10]


def test_fact_metrics_are_scoped_to_filing_accession_and_derive_values() -> None:
    accession = "0000000000-26-000001"

    def row(value: int, start: str, end: str, accn: str = accession) -> dict:
        return {"val": value, "start": start, "end": end, "accn": accn, "form": "10-K"}

    facts = {"facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [row(100, "2024-01-01", "2024-12-31"), row(125, "2025-01-01", "2025-12-31"), row(999, "2025-01-01", "2025-12-31", "other")] }},
        "OperatingIncomeLoss": {"units": {"USD": [row(25, "2025-01-01", "2025-12-31")]}},
        "NetIncomeLoss": {"units": {"USD": [row(20, "2025-01-01", "2025-12-31")]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [row(30, "2025-01-01", "2025-12-31")]}},
        "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": [row(8, "2025-01-01", "2025-12-31")]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [{"val": 50, "end": "2025-12-31", "accn": accession, "form": "10-K"}]}},
    }}}
    filing = Filing(Ticker.AAPL, accession, date(2026, 2, 1), 2025, "https://www.sec.gov/Archives/edgar/data/1/f.htm", "", facts)
    result = extract_fundamental_metrics(filing)
    assert result["revenue"]["value"] == 125
    assert result["revenue_yoy_growth_pct"]["value"] == 25
    assert result["operating_margin_pct"]["value"] == 20
    assert result["free_cash_flow"]["value"] == 22


def test_sec_contact_email_required() -> None:
    with pytest.raises(ProviderError, match="SEC_USER_AGENT"):
        _headers(Settings(sec_user_agent="FinSightAI/1.0 your-email@example.com"))
