from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_preflight_from_any_origin_is_allowed() -> None:
    response = client.options(
        "/api/v1/ready",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_actual_response_includes_cors_headers_for_browser_fetch() -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:3001"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_cors_never_allows_credentials_with_wildcard_origin() -> None:
    response = client.options(
        "/api/v1/ready",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-credentials" not in response.headers
