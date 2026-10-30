from datetime import timezone

import pandas as pd

from app.api.schemas import MetricValue
from app.services.technical_indicators import (
    compute_metrics,
    period_return,
    rsi14,
    simple_moving_average,
    volatility_note,
    volume_observation,
)


def _frame(closes: list[float], volumes: list[float] | None = None) -> pd.DataFrame:
    index = pd.date_range("2024-01-02", periods=len(closes), freq="B", tz=timezone.utc)
    vols = volumes if volumes is not None else [1_000_000.0] * len(closes)
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [value * 1.01 for value in closes],
            "Low": [value * 0.99 for value in closes],
            "Close": closes,
            "Volume": vols,
        },
        index=index,
    )


def test_daily_and_multi_day_returns() -> None:
    close = _frame([100.0, 110.0, 121.0])["Close"]
    daily = period_return(close, 1, "Daily percentage change")
    assert daily.value is not None
    assert abs(daily.value - 10.0) < 1e-9
    five = period_return(close, 5, "Five-trading-day return")
    assert five.value is None
    assert five.unavailable_reason is not None


def test_sma20_and_sma50() -> None:
    values = [float(i) for i in range(1, 21)]
    close = _frame(values)["Close"]
    sma20 = simple_moving_average(close, 20)
    assert sma20.value == 10.5
    sma50 = simple_moving_average(close, 50)
    assert sma50.value is None
    assert "50" in (sma50.unavailable_reason or "")


def test_rsi_rising_series_is_high() -> None:
    close = _frame([float(100 + i) for i in range(30)])["Close"]
    metric = rsi14(close)
    assert metric.value is not None
    assert metric.value > 70


def test_rsi_insufficient_data() -> None:
    close = _frame([100.0, 101.0, 102.0])["Close"]
    metric = rsi14(close)
    assert metric.value is None
    assert metric.unavailable_reason is not None


def test_missing_values_do_not_crash() -> None:
    frame = _frame([100.0, 101.0] + [float("nan")] * 5 + [110.0] * 20)
    metrics = compute_metrics(frame)
    assert isinstance(metrics["latest_close"], MetricValue)
    assert metrics["latest_close"].value == 110.0
    incomplete_recent = pd.Series([100.0, float("nan"), 102.0])
    missing_daily = period_return(incomplete_recent, 1, "Daily percentage change")
    assert missing_daily.value is None
    assert "missing" in (missing_daily.unavailable_reason or "")


def test_zero_price_return() -> None:
    close = _frame([0.0, 10.0])["Close"]
    metric = period_return(close, 1, "Daily percentage change")
    assert metric.value is None
    assert metric.unavailable_reason is not None


def test_volume_comparison() -> None:
    volumes = [1_000_000.0] * 20 + [2_000_000.0]
    note = volume_observation(_frame([100.0] * 21, volumes)["Volume"])
    assert "2.00x" in note
    assert "well above" in note
    volumes[-1] = float("nan")
    assert "latest volume" in volume_observation(_frame([100.0] * 21, volumes)["Volume"])


def test_volatility_insufficient() -> None:
    note = volatility_note(_frame([100.0, 101.0])["Close"])
    assert note.startswith("Unavailable")
