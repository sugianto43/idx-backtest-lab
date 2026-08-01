from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_response_includes_generated_correlation_id_header() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("x-correlation-id")


def test_response_preserves_supplied_correlation_id_header() -> None:
    response = client.get("/health", headers={"X-Correlation-Id": "test-correlation-123"})

    assert response.headers["x-correlation-id"] == "test-correlation-123"
