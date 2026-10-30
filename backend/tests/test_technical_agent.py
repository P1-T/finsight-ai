from datetime import timezone

import pandas as pd

from app.agents.technical_agent import TechnicalLlmOutput, analyze_technical
from app.api.schemas import Ticker
from app.providers.market_data_provider import MarketHistory
from app.utils.errors import ProviderError


class FakeStructured:
    def __init__(self, payload: TechnicalLlmOutput) -> None:
        self.payload = payload

    def invoke(self, _messages: object) -> TechnicalLlmOutput:
        return self.payload


class FakeLLM:
    def __init__(self, payload: TechnicalLlmOutput) -> None:
        self.payload = payload

    def with_structured_output(self, _schema: object, method: str = "json_schema") -> FakeStructured:
        return FakeStructured(self.payload)


def _history(n: int = 60) -> MarketHistory:
    closes = [100.0 + i * 0.2 for i in range(n)]
    index = pd.date_range("2024-01-02", periods=n, freq="B", tz=timezone.utc)
    frame = pd.DataFrame(
        {
            "Open": closes,
            "High": [value + 1 for value in closes],
            "Low": [value - 1 for value in closes],
            "Close": closes,
            "Volume": [1_000_000.0] * n,
        },
        index=index,
    )
    return MarketHistory(ticker=Ticker.MSFT, frame=frame, as_of_date=index[-1].date())


def test_technical_agent_success(monkeypatch) -> None:
    class Provider:
        def fetch(self, ticker):
            return _history()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    llm_out = TechnicalLlmOutput(
        short_term_trend="Price is above SMA20.",
        medium_term_trend="Price is above SMA50.",
        momentum="RSI is elevated but not a signal.",
        volume_commentary="Volume is near average.",
        caveats=["Historical only."],
    )
    technical, chart = analyze_technical(Ticker.MSFT, provider=Provider(), llm=FakeLLM(llm_out))  # type: ignore[arg-type]
    assert technical.status == "succeeded"
    assert technical.latest_close.value is not None
    assert technical.as_of_date is not None
    assert len(chart.candles) > 0
    get_settings.cache_clear()


def test_technical_agent_provider_failure() -> None:
    class Provider:
        def fetch(self, ticker):
            raise ProviderError("Market data provider (yfinance) is unavailable or returned an error.")

    technical, chart = analyze_technical(Ticker.MSFT, provider=Provider())  # type: ignore[arg-type]
    assert technical.status == "failed"
    assert chart.candles == []
