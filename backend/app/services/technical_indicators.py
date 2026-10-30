from __future__ import annotations

from datetime import date

import pandas as pd

from app.api.schemas import ChartPoint, ChartSeries, MetricValue, OverlayPoint
from app.constants import CHART_TRADING_DAYS


def _last_valid(series: pd.Series) -> float | None:
    if series.empty:
        return None
    value = series.iloc[-1]
    if pd.isna(value):
        return None
    return float(value)


def period_return(close: pd.Series, periods: int, label: str) -> MetricValue:
    if len(close) < periods + 1:
        return MetricValue(
            unavailable_reason=f"{label} requires at least {periods + 1} closing prices."
        )
    window = close.tail(periods + 1)
    if window.isna().any():
        return MetricValue(unavailable_reason=f"{label} is unavailable because a required session close is missing.")
    start = window.iloc[0]
    end = window.iloc[-1]
    if start == 0 or pd.isna(start) or pd.isna(end):
        return MetricValue(unavailable_reason=f"{label} cannot be computed from a zero or missing price.")
    return MetricValue(value=float((end / start) - 1) * 100)


def simple_moving_average(close: pd.Series, window: int) -> MetricValue:
    if close.dropna().shape[0] < window:
        return MetricValue(unavailable_reason=f"SMA{window} requires at least {window} closing prices.")
    sma = close.rolling(window=window, min_periods=window).mean()
    value = _last_valid(sma)
    if value is None:
        return MetricValue(unavailable_reason=f"SMA{window} is unavailable for the latest session.")
    return MetricValue(value=value)


def rsi14(close: pd.Series) -> MetricValue:
    usable = close.dropna()
    if len(usable) < 15:
        return MetricValue(unavailable_reason="RSI14 requires at least 15 closing prices.")
    delta = usable.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    if pd.isna(last_gain) or pd.isna(last_loss):
        return MetricValue(unavailable_reason="RSI14 is unavailable for the latest session.")
    if last_loss == 0 and last_gain == 0:
        return MetricValue(value=50.0)
    if last_loss == 0:
        return MetricValue(value=100.0)
    rs = last_gain / last_loss
    return MetricValue(value=float(100 - (100 / (1 + rs))))


def volume_observation(volume: pd.Series) -> str:
    if len(volume) < 21:
        return "Unavailable: volume comparison requires at least 21 sessions."
    latest = volume.iloc[-1]
    baseline = volume.iloc[-21:-1]
    if baseline.isna().any() or pd.isna(latest):
        return "Unavailable: latest volume or one of the prior 20 session volumes is missing."
    average = baseline.mean()
    if pd.isna(average) or average == 0 or pd.isna(latest):
        return "Unavailable: volume average could not be computed without a zero or missing baseline."
    ratio = float(latest / average)
    if ratio >= 1.5:
        qualifier = "well above"
    elif ratio >= 1.15:
        qualifier = "above"
    elif ratio <= 0.5:
        qualifier = "well below"
    elif ratio <= 0.85:
        qualifier = "below"
    else:
        qualifier = "near"
    return (
        f"Latest volume is {qualifier} the prior 20-session average "
        f"({ratio:.2f}x the 20-session mean). This is not a trading signal."
    )


def volatility_note(close: pd.Series) -> str:
    usable = close.dropna()
    if len(usable) < 21:
        return "Unavailable: 20-session volatility requires at least 21 closing prices."
    daily = usable.pct_change().dropna()
    if len(daily) < 20:
        return "Unavailable: 20-session volatility requires at least 20 daily returns."
    stdev = daily.iloc[-20:].std(ddof=1)
    if pd.isna(stdev):
        return "Unavailable: volatility could not be computed from the recent returns."
    return (
        f"20-session standard deviation of daily returns is {float(stdev) * 100:.2f}%. "
        "This is a historical dispersion statistic, not a forecast."
    )


def sma_series(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=window).mean()


def build_chart_series(frame: pd.DataFrame, trading_days: int = CHART_TRADING_DAYS) -> ChartSeries:
    window = frame.tail(trading_days)
    sma20 = sma_series(frame["Close"], 20).reindex(window.index)
    sma50 = sma_series(frame["Close"], 50).reindex(window.index)

    candles: list[ChartPoint] = []
    sma20_points: list[OverlayPoint] = []
    sma50_points: list[OverlayPoint] = []

    for idx, row in window.iterrows():
        session: date = idx.date() if hasattr(idx, "date") else pd.Timestamp(idx).date()
        if pd.isna(row["Open"]) or pd.isna(row["High"]) or pd.isna(row["Low"]) or pd.isna(row["Close"]):
            continue
        candles.append(
            ChartPoint(
                time=session,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]) if not pd.isna(row["Volume"]) else 0.0,
            )
        )
        sma20_val = sma20.loc[idx]
        sma50_val = sma50.loc[idx]
        if not pd.isna(sma20_val):
            sma20_points.append(OverlayPoint(time=session, value=float(sma20_val)))
        if not pd.isna(sma50_val):
            sma50_points.append(OverlayPoint(time=session, value=float(sma50_val)))

    return ChartSeries(candles=candles, sma20=sma20_points, sma50=sma50_points)


def compute_metrics(frame: pd.DataFrame) -> dict[str, MetricValue | str]:
    close = frame["Close"]
    volume = frame["Volume"]
    latest = _last_valid(close)
    latest_close = (
        MetricValue(value=latest)
        if latest is not None
        else MetricValue(unavailable_reason="Latest close is missing.")
    )
    return {
        "latest_close": latest_close,
        "daily_pct_change": period_return(close, 1, "Daily percentage change"),
        "return_5d": period_return(close, 5, "Five-trading-day return"),
        "return_20d": period_return(close, 20, "Twenty-trading-day return"),
        "sma20": simple_moving_average(close, 20),
        "sma50": simple_moving_average(close, 50),
        "rsi14": rsi14(close),
        "volume_vs_average": volume_observation(volume),
        "volatility_note": volatility_note(close),
    }


def compact_price_context(frame: pd.DataFrame, last_n: int = 15) -> list[dict[str, float | str | None]]:
    rows: list[dict[str, float | str | None]] = []
    for idx, row in frame.tail(last_n).iterrows():
        session = idx.date() if hasattr(idx, "date") else pd.Timestamp(idx).date()
        if pd.isna(row["Close"]):
            continue
        rows.append(
            {
                "date": session.isoformat(),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]) if not pd.isna(row["Volume"]) else None,
            }
        )
    return rows
