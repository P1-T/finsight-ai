import json

from app.agents.fundamental_agent import FundamentalLlmOutput, analyze_fundamental
from app.api.schemas import Ticker


class FakeStore:
    def search(self, ticker, query, top_k=4, filter=None):
        metadata = {
            "filing_date": "2026-02-01",
            "fiscal_year": 2025,
            "filing_url": "https://www.sec.gov/Archives/edgar/data/1/filing.htm",
            "record_type": "metric_facts",
            "metrics_json": json.dumps({
                "revenue": {"value": 125000, "unit": "USD", "fiscal_year": 2025},
                "revenue_yoy_growth_pct": {"value": 25, "unit": "percent", "fiscal_year": 2025},
            }),
        }
        return [
            {"_id": "facts", "fields": metadata},
            {"_id": "chunk-1", "fields": {
                **metadata,
                "record_type": "section_chunk",
                "section": "Item 1A. Risk Factors",
                "chunk_text": "The company reports competition and regulatory risks.",
                "citation_url": "https://www.sec.gov/Archives/edgar/data/1/filing.htm",
            }},
        ]


class FakeStructured:
    def invoke(self, messages):
        return FundamentalLlmOutput(
            overview="The filing describes its business and risks.",
            business_findings=[{"topic": "Business", "finding": "The company discusses its markets.", "source_ids": ["chunk-1", "external-id"]}],
            key_risks=[],
            limitations=[],
        )


class FakeModel:
    def with_structured_output(self, *args, **kwargs):
        return FakeStructured()


def test_fundamental_agent_validates_citations_and_returns_filing_metrics(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.fundamental_agent.require_api_key", lambda: "configured")
    result = analyze_fundamental(Ticker.AAPL, store=FakeStore(), llm=FakeModel())
    assert result.status == "succeeded"
    assert result.revenue.value == 125000
    assert result.revenue_yoy_growth_pct.value == 25
    assert result.business_findings[0].citation_urls == ["https://www.sec.gov/Archives/edgar/data/1/filing.htm"]
    assert len(result.citations) == 1


def test_missing_filing_returns_no_evidence_without_model_call() -> None:
    class EmptyStore:
        def search(self, ticker, query, top_k=4, filter=None):
            return []

    result = analyze_fundamental(Ticker.NVDA, store=EmptyStore(), llm=FakeModel())
    assert result.status == "no_evidence"
    assert "ingest" in result.limitations[0]
