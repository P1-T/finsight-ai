from fastapi.testclient import TestClient


def test_stocks(client: TestClient) -> None:
    response = client.get("/api/stocks")
    assert response.status_code == 200
    payload = response.json()
    tickers = [item["ticker"] for item in payload["stocks"]]
    names = {item["ticker"]: item["name"] for item in payload["stocks"]}
    assert tickers == ["AAPL", "NVDA", "MSFT"]
    assert names["AAPL"] == "Apple Inc."
    assert names["NVDA"] == "NVIDIA Corporation"
    assert names["MSFT"] == "Microsoft Corporation"
