from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd

from app.api.schemas import Ticker
from app.config import Settings, get_settings
from app.constants import MARKET_HISTORY_PERIOD
from app.utils.errors import ProviderError


@dataclass(frozen=True)
class MarketHistory:
    ticker: Ticker
    frame: pd.DataFrame
    as_of_date: date


class MarketDataProvider(Protocol):
    def fetch(self, ticker: Ticker, period: str = MARKET_HISTORY_PERIOD) -> MarketHistory: ...


def _flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        frame = frame.copy()
        frame.columns = [str(col[0]).title() if isinstance(col, tuple) else str(col) for col in frame.columns]
    else:
        frame = frame.copy()
        frame.columns = [str(col).title() for col in frame.columns]
    return frame


def normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ProviderError("Market data provider returned no historical rows.")

    frame = _flatten_columns(frame)
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ProviderError("Market data provider returned an incomplete OHLCV schema.")

    out = frame[required].copy()
    out.index = pd.to_datetime(out.index, utc=True)
    out = out.sort_index()
    out = out.dropna(how="all")
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["Close"])
    if out.empty:
        raise ProviderError("Market data provider returned no usable closing prices.")
    return out


class YFinanceMarketDataProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def fetch(self, ticker: Ticker, period: str = MARKET_HISTORY_PERIOD) -> MarketHistory:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ProviderError("Market data library is not installed.") from exc

        try:
            history = yf.Ticker(ticker.value).history(
                period=period,
                interval="1d",
                auto_adjust=False,
                timeout=self._settings.market_data_timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - yfinance raises varied errors
            raise ProviderError("Market data provider (yfinance) is unavailable or returned an error.") from exc

        frame = normalize_ohlcv(history)
        as_of = frame.index[-1].date()
        return MarketHistory(ticker=ticker, frame=frame, as_of_date=as_of)
