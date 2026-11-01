from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass

import httpx

from app.config import Settings, get_settings
from app.utils.errors import ProviderError

logger = logging.getLogger(__name__)
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
# Common public-facing brand names that differ substantially from their SEC legal names.
COMPANY_ALIASES = {"google": "GOOGL", "alphabet": "GOOGL", "oracle": "ORCL"}
COMMON_WORDS = {
    "a", "am", "an", "and", "are", "as", "at", "be", "but", "by", "can", "compare",
    "do", "for", "from", "go", "has", "have", "he", "her", "here", "how", "i", "if",
    "in", "is", "it", "its", "me", "my", "news", "no", "of", "on", "or", "our", "out",
    "price", "stock", "stocks", "the", "their", "them", "there", "they", "this", "to", "up",
    "us", "was", "we", "were", "what", "when", "which", "who", "why", "will", "with", "you",
    "ai", "cfo", "ceo", "cpi", "dcf", "eps", "etf", "etfs", "fed", "gdp", "ipo", "ipos",
    "nyse", "nasdaq", "pe", "rsi", "sec", "sma", "usa", "usd",
}


def _searchable_company_name(name: str) -> str:
    normalized = name.casefold()
    normalized = re.sub(r"\b(incorporated|inc|corporation|corp|company|co|limited|ltd|plc)\b", "", normalized)
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", normalized).split()).strip()


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    exchange: str


class CompanyDirectory:
    """Cached SEC exchange-listed symbol directory with a bounded search API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._companies: tuple[Company, ...] = ()
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def all(self) -> tuple[Company, ...]:
        with self._lock:
            if self._companies and time.monotonic() < self._expires_at:
                return self._companies
            try:
                headers = {"User-Agent": self.settings.sec_user_agent}
                with httpx.Client(timeout=self.settings.sec_timeout_seconds) as client:
                    response = client.get(SEC_TICKERS_URL, headers=headers)
                    response.raise_for_status()
                payload = response.json()
                fields = payload.get("fields", [])
                positions = {name: fields.index(name) for name in ("name", "ticker", "exchange")}
                values: dict[str, Company] = {}
                for row in payload.get("data", []):
                    if not isinstance(row, list) or len(row) <= max(positions.values()):
                        continue
                    name = str(row[positions["name"]] or "").strip()
                    ticker = str(row[positions["ticker"]] or "").strip().upper()
                    exchange = str(row[positions["exchange"]] or "").strip()
                    if not name or not ticker or not exchange or "OTC" in exchange.upper():
                        continue
                    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,14}", ticker):
                        continue
                    values.setdefault(ticker, Company(ticker=ticker, name=name, exchange=exchange))
                if not values:
                    raise ValueError("SEC ticker directory had no exchange-listed entries.")
                self._companies = tuple(sorted(values.values(), key=lambda item: item.ticker))
                self._expires_at = time.monotonic() + max(60, self.settings.company_directory_cache_seconds)
            except Exception as exc:
                if self._companies:
                    logger.warning("SEC ticker directory refresh failed; serving stale cache")
                    self._expires_at = time.monotonic() + 300
                    return self._companies
                raise ProviderError("The US-listed company directory is temporarily unavailable.") from exc
            return self._companies

    def search(self, query: str = "", limit: int = 12) -> list[Company]:
        companies = self.all()
        query = query.strip().lstrip("$").strip().casefold()
        bounded_limit = max(1, min(limit, 25))
        if not query:
            return []
        alias_ticker = COMPANY_ALIASES.get(query)
        if alias_ticker:
            alias_company = next((company for company in companies if company.ticker == alias_ticker), None)
            if alias_company:
                return [alias_company]
        allow_ticker_prefix = len(query) >= 3
        matches = [
            company
            for company in companies
            if query in company.name.casefold()
            or (allow_ticker_prefix and company.ticker.casefold().startswith(query))
        ]
        matches.sort(
            key=lambda company: (
                0 if company.ticker.casefold() == query else
                1 if company.name.casefold().startswith(query) else
                2 if company.ticker.casefold().startswith(query) else
                3,
                company.ticker,
            )
        )
        return matches[:bounded_limit]

    def find(self, ticker: str) -> Company | None:
        symbol = ticker.strip().upper()
        return next((company for company in self.all() if company.ticker == symbol), None)

    def mentions(self, prompt: str, maximum: int = 4) -> list[Company]:
        companies = self.all()
        symbols = {company.ticker: company for company in companies}
        mentioned: list[Company] = []
        for match in re.finditer(r"(?<![A-Za-z0-9])\$?([A-Za-z][A-Za-z0-9.-]{0,14})(?![A-Za-z0-9])", prompt):
            raw_symbol = match.group(1)
            if not match.group(0).startswith("$") and raw_symbol.casefold() in COMMON_WORDS:
                continue
            if company := symbols.get(raw_symbol.upper()):
                if company not in mentioned:
                    mentioned.append(company)
        lowered = prompt.casefold()
        explicit_names = {_searchable_company_name(company.name) for company in mentioned}
        for alias, ticker in COMPANY_ALIASES.items():
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered):
                if company := symbols.get(ticker):
                    if company not in mentioned:
                        mentioned.append(company)
                    explicit_names.add(_searchable_company_name(company.name))
        if len(mentioned) < maximum:
            names = sorted(companies, key=lambda company: len(company.name), reverse=True)
            for company in names:
                searchable = _searchable_company_name(company.name)
                # An exact ticker in the prompt selects that security over other listings
                # that happen to share the same legal/display name.
                if searchable in explicit_names and company not in mentioned:
                    continue
                if searchable and re.search(rf"(?<!\w){re.escape(searchable)}(?!\w)", lowered):
                    if company not in mentioned:
                        mentioned.append(company)
                        if len(mentioned) >= maximum:
                            break
        return mentioned[:maximum]


company_directory = CompanyDirectory()
