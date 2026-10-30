import pandas as pd
import pytest

from app.providers.market_data_provider import normalize_ohlcv
from app.utils.errors import ProviderError


def test_normalize_ohlcv_sorts_and_coerces_values() -> None:
    frame = pd.DataFrame(
        {
            "open": ["11", "10"],
            "high": ["12", "11"],
            "low": ["9", "9"],
            "close": ["11.5", "10.5"],
            "volume": ["120", "100"],
        },
        index=["2025-01-03", "2025-01-02"],
    )
    result = normalize_ohlcv(frame)
    assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert result.index.is_monotonic_increasing
    assert result.iloc[0]["Close"] == 10.5
    assert result.iloc[0]["Volume"] == 100


@pytest.mark.parametrize(
    "frame",
    [pd.DataFrame(), pd.DataFrame({"Open": [1], "Close": [1]})],
)
def test_normalize_ohlcv_rejects_empty_or_incomplete_data(frame: pd.DataFrame) -> None:
    with pytest.raises(ProviderError):
        normalize_ohlcv(frame)
