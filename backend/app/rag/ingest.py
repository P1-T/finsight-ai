from __future__ import annotations

import argparse
import json
import logging
import re
import time
from typing import Any

from app.api.schemas import Ticker
from app.rag.pinecone_store import PineconeFilingStore
from app.rag.sec_edgar import (
    chunk_sections,
    extract_fundamental_metrics,
    extract_sections,
    fetch_latest_10k,
)

logger = logging.getLogger(__name__)


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", value)


def ingest_ticker(ticker: Ticker, store: PineconeFilingStore | None = None) -> int:
    filing = fetch_latest_10k(ticker)
    sections = extract_sections(filing.html)
    chunks = chunk_sections(sections)
    metrics = extract_fundamental_metrics(filing)
    if not chunks:
        raise RuntimeError(f"No usable filing chunks for {ticker.value}.")
    manifest_text = "Filing financial facts: " + json.dumps(metrics, separators=(",", ":"))
    url = filing.url
    docs: list[dict[str, Any]] = [{
        "_id": f"{ticker.value}-{_safe_id(filing.accession)}-facts",
        "chunk_text": manifest_text,
        "section": "Filing financial metrics",
        "record_type": "metric_facts",
        "filing_date": filing.filing_date.isoformat(),
        "fiscal_year": filing.fiscal_year,
        "filing_url": url,
        "citation_url": url,
        "accession": filing.accession,
        "metrics_json": json.dumps(metrics, separators=(",", ":")),
    }]
    for number, chunk in enumerate(chunks):
        docs.append({
            "_id": f"{ticker.value}-{_safe_id(filing.accession)}-{number:04d}",
            "chunk_text": chunk["text"],
            "section": chunk["section"],
            "record_type": "section_chunk",
            "filing_date": filing.filing_date.isoformat(),
            "fiscal_year": filing.fiscal_year,
            "filing_url": url,
            "citation_url": url,
            "accession": filing.accession,
        })
    pinecone = store or PineconeFilingStore()
    pinecone.ensure_index()
    current_filing_filter = {
        "accession": {"$eq": filing.accession},
        "record_type": {"$eq": "metric_facts"},
    }
    already_indexed = pinecone.search(ticker, manifest_text, top_k=1, filter=current_filing_filter)
    if already_indexed:
        logger.info("Current %s 10-K accession is already indexed; skipping embedding and upsert.", ticker.value)
    else:
        pinecone.ingest(ticker, filing.accession, docs)
        # Give serverless indexing a moment to surface the new chunks before removing old filing data.
        for _ in range(10):
            if pinecone.search(ticker, manifest_text, top_k=1, filter=current_filing_filter):
                break
            time.sleep(2)
        else:
            raise RuntimeError("Pinecone did not return the ingested filing for verification.")
    pinecone.replace_old_filings(ticker, filing.accession)
    return len(docs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the latest SEC 10-K filing into Pinecone.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticker", choices=[ticker.value for ticker in Ticker])
    group.add_argument("--all", action="store_true", help="Ingest latest 10-K for AAPL, NVDA, and MSFT.")
    args = parser.parse_args()
    tickers = list(Ticker) if args.all else [Ticker(args.ticker)]
    for ticker in tickers:
        count = ingest_ticker(ticker)
        print(f"{ticker.value}: {count} documents confirmed for the latest filing.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
