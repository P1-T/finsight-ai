from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    body = response.json()
    assert "anthropic" not in str(body).lower()
    assert "api_key" not in str(body).lower()
