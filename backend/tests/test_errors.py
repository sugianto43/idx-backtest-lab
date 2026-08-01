from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import app, create_app


class _Payload(BaseModel):
    name: str


def _build_test_app() -> FastAPI:
    test_app = create_app()

    @test_app.post("/__test__/validate")
    def _validate(payload: _Payload) -> dict[str, str]:
        return {"name": payload.name}

    @test_app.get("/__test__/boom")
    def _boom() -> None:
        raise RuntimeError("boom")

    return test_app


def test_unknown_route_returns_not_found_envelope() -> None:
    client = TestClient(app)

    response = client.get("/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["correlation_id"]


def test_validation_failure_returns_validation_error_envelope() -> None:
    client = TestClient(_build_test_app())

    response = client.post("/__test__/validate", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]
    assert body["error"]["correlation_id"]


def test_unhandled_exception_returns_internal_error_envelope_without_leaking_details() -> None:
    client = TestClient(_build_test_app(), raise_server_exceptions=False)

    response = client.get("/__test__/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "boom" not in response.text
    assert "RuntimeError" not in response.text
