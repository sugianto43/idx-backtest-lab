from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.settings import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_ready_returns_200_after_startup_migrations(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("APP_DATABASE_PATH", str(tmp_path / "ready.duckdb"))

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "idx-backtesting-lab-api"
    assert body["database"] == "ready"


def test_ready_returns_503_when_migrations_have_not_run(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("APP_DATABASE_PATH", str(tmp_path / "not_ready.duckdb"))

    app = create_app()
    client = TestClient(app)  # not entered as a context manager: startup migrations do not run

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "dependency_unavailable"
    assert body["error"]["correlation_id"]


def test_health_remains_database_independent(tmp_path: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("APP_DATABASE_PATH", str(tmp_path / "unused.duckdb"))

    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
