from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.api.schemas import Ticker
from app.config import Settings, get_settings
from app.utils.errors import ProviderError

logger = logging.getLogger(__name__)


class PineconeFilingStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.pinecone_api_key.strip():
            raise ProviderError("Pinecone API key is not configured on the server.")
        from pinecone import Pinecone, ServerlessSpec

        self.client = Pinecone(api_key=self.settings.pinecone_api_key)
        self._serverless_spec = ServerlessSpec(
            cloud=self.settings.pinecone_cloud,
            region=self.settings.pinecone_region,
        )

    def ensure_index(self) -> None:
        name = self.settings.pinecone_index_name
        if not self.client.has_index(name):
            self.client.indexes.create(
                name=name,
                spec=self._serverless_spec,
                schema={"fields": {"chunk_text": {"type": "string", "embed": {"model": self.settings.pinecone_embed_model}}}},
            )
        for _ in range(30):
            description = self.client.describe_index(name)
            status = getattr(description, "status", None)
            ready = status.get("ready", False) if isinstance(status, dict) else getattr(status, "ready", False)
            if ready:
                return
            time.sleep(2)
        raise ProviderError("Pinecone index is not ready yet. Try the ingestion command again shortly.")

    def _index(self, ticker: Ticker):
        description = self.client.describe_index(self.settings.pinecone_index_name)
        host = getattr(description, "host", None)
        if host:
            return self.client.index(host=host)
        return self.client.index(name=self.settings.pinecone_index_name)

    def ingest(self, ticker: Ticker, accession: str, documents: list[dict[str, Any]]) -> None:
        index = self._index(ticker)
        for start in range(0, len(documents), 96):
            index.documents.upsert(namespace=ticker.value, documents=documents[start : start + 96])

    @staticmethod
    def _hits(response: Any) -> list[dict[str, Any]]:
        if hasattr(response, "to_dict"):
            response = response.to_dict()
        if not isinstance(response, dict):
            return []
        # The current Python Documents API SDK serializes search results as
        # top-level `matches`; the REST examples use `result.hits`.
        matches = response.get("matches")
        if isinstance(matches, list):
            return [match for match in matches if isinstance(match, dict)]
        result = response.get("result", response)
        if hasattr(result, "to_dict"):
            result = result.to_dict()
        hits = result.get("hits", []) if isinstance(result, dict) else []
        return [hit for hit in hits if isinstance(hit, dict)]

    def search(
        self,
        ticker: Ticker,
        query: str,
        top_k: int = 4,
        filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        index = self._index(ticker)
        response = index.documents.search(
            namespace=ticker.value,
            top_k=top_k,
            score_by=[{"type": "embed", "fields": ["chunk_text"], "query": query}],
            include_fields=["chunk_text", "section", "record_type", "filing_date", "fiscal_year", "filing_url", "metrics_json", "citation_url", "accession"],
            filter=filter,
        )
        return self._hits(response)

    def replace_old_filings(self, ticker: Ticker, accession: str) -> None:
        index = self._index(ticker)
        # Filter deletion is intentionally after current accession ingestion.
        index.documents.delete(namespace=ticker.value, filter={"accession": {"$ne": accession}})


def metric_payload_from_hits(hits: list[dict[str, Any]]) -> dict[str, Any] | None:
    for hit in hits:
        fields = hit.get("fields", hit)
        encoded = fields.get("metrics_json") if isinstance(fields, dict) else None
        if isinstance(encoded, str):
            try:
                value = json.loads(encoded)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                logger.warning("Ignoring malformed filing metric metadata returned by Pinecone")
    return None


def citation_from_hit(hit: dict[str, Any]) -> dict[str, str] | None:
    fields = hit.get("fields", hit)
    if not isinstance(fields, dict):
        return None
    text = fields.get("chunk_text")
    section = fields.get("section")
    url = fields.get("citation_url")
    if not all(isinstance(value, str) and value for value in (text, section, url)):
        return None
    return {"text": text, "section": section, "url": url}
