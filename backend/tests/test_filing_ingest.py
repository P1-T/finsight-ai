from datetime import date

from app.api.schemas import Ticker
from app.rag.ingest import ingest_ticker
from app.rag.sec_edgar import Filing


class ExistingFilingStore:
    def __init__(self):
        self.deleted = False
        self.upserted = False

    def ensure_index(self):
        pass

    def search(self, ticker, query, top_k=4, filter=None):
        return [{"_id": "existing-facts"}]

    def ingest(self, ticker, accession, documents):
        self.upserted = True

    def replace_old_filings(self, ticker, accession):
        self.deleted = True


def test_ingestion_retry_skips_embedding_when_current_filing_already_exists(monkeypatch) -> None:
    filing = Filing(
        ticker=Ticker.AAPL,
        accession="0000320193-25-000079",
        filing_date=date(2025, 10, 31),
        fiscal_year=2025,
        url="https://www.sec.gov/Archives/edgar/data/320193/filing.htm",
        html="unused",
        company_facts={},
    )
    store = ExistingFilingStore()
    monkeypatch.setattr("app.rag.ingest.fetch_latest_10k", lambda ticker: filing)
    monkeypatch.setattr("app.rag.ingest.extract_sections", lambda html: {"Item 1. Business": "Business evidence."})
    monkeypatch.setattr("app.rag.ingest.extract_fundamental_metrics", lambda filing: {"revenue": {"value": 1}})

    count = ingest_ticker(Ticker.AAPL, store=store)
    assert count == 2
    assert store.upserted is False
    assert store.deleted is True
