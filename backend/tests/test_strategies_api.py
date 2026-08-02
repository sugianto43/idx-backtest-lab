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


@pytest.fixture
def client(tmp_path: Any, monkeypatch: Any) -> Iterator[TestClient]:
    monkeypatch.setenv("APP_DATABASE_PATH", str(tmp_path / "test.duckdb"))
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


VALID_PAYLOAD = {
    "name": "SMA crossover 10/30",
    "kind": "sma_crossover",
    "parameters": {"fast_window": 10, "slow_window": 30, "price_field": "close"},
    "signal_policy": {"signal_time": "bar_close", "eligible_after_bars": 30, "long_only": True},
}


def test_create_strategy_returns_201(client: TestClient) -> None:
    response = client.post("/api/v1/strategies", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["version"] == 1
    assert body["checksum"].startswith("sha256:")


def test_create_strategy_rejects_fast_not_less_than_slow(client: TestClient) -> None:
    payload = {
        **VALID_PAYLOAD,
        "parameters": {"fast_window": 30, "slow_window": 30, "price_field": "close"},
    }
    response = client.post("/api/v1/strategies", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_strategy_rejects_unsupported_price_field(client: TestClient) -> None:
    payload = {
        **VALID_PAYLOAD,
        "parameters": {"fast_window": 10, "slow_window": 30, "price_field": "vwap"},
    }
    response = client.post("/api/v1/strategies", json=payload)

    assert response.status_code == 422


def test_get_strategy_version_round_trip(client: TestClient) -> None:
    created = client.post("/api/v1/strategies", json=VALID_PAYLOAD).json()

    response = client.get(f"/api/v1/strategies/{created['strategy_id']}/versions/1")

    assert response.status_code == 200
    assert response.json()["checksum"] == created["checksum"]


def test_get_unknown_strategy_version_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/strategies/does-not-exist/versions/1")
    assert response.status_code == 404


def test_list_strategies_paginates(client: TestClient) -> None:
    client.post("/api/v1/strategies", json=VALID_PAYLOAD)
    client.post("/api/v1/strategies", json=VALID_PAYLOAD)

    response = client.get("/api/v1/strategies", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1


def test_create_strategy_rejects_unsupported_kind(client: TestClient) -> None:
    payload = {**VALID_PAYLOAD, "kind": "does_not_exist"}
    response = client.post("/api/v1/strategies", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["code"] == "unsupported_kind"


def test_create_rsi_threshold_strategy_returns_201(client: TestClient) -> None:
    payload = {
        "name": "RSI 14 30/70",
        "kind": "rsi_threshold",
        "parameters": {
            "period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
            "price_field": "close",
        },
        "signal_policy": {
            "signal_time": "bar_close",
            "eligible_after_bars": 15,
            "long_only": True,
        },
    }
    response = client.post("/api/v1/strategies", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "rsi_threshold"
    assert body["parameters"]["period"] == 14


def test_create_rsi_threshold_strategy_rejects_bad_threshold_order(client: TestClient) -> None:
    payload = {
        "name": "RSI bad thresholds",
        "kind": "rsi_threshold",
        "parameters": {
            "period": 14,
            "oversold_threshold": 70,
            "overbought_threshold": 30,
            "price_field": "close",
        },
        "signal_policy": {
            "signal_time": "bar_close",
            "eligible_after_bars": 15,
            "long_only": True,
        },
    }
    response = client.post("/api/v1/strategies", json=payload)

    assert response.status_code == 422


def test_create_macd_crossover_strategy_returns_201(client: TestClient) -> None:
    payload = {
        "name": "MACD 12/26/9",
        "kind": "macd_crossover",
        "parameters": {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "price_field": "close",
        },
        "signal_policy": {
            "signal_time": "bar_close",
            "eligible_after_bars": 35,
            "long_only": True,
        },
    }
    response = client.post("/api/v1/strategies", json=payload)

    assert response.status_code == 201
    assert response.json()["kind"] == "macd_crossover"


def test_create_bollinger_breakout_strategy_returns_201(client: TestClient) -> None:
    payload = {
        "name": "Bollinger 20/2",
        "kind": "bollinger_breakout",
        "parameters": {"period": 20, "num_std_dev": 2, "price_field": "close"},
        "signal_policy": {
            "signal_time": "bar_close",
            "eligible_after_bars": 20,
            "long_only": True,
        },
    }
    response = client.post("/api/v1/strategies", json=payload)

    assert response.status_code == 201
    assert response.json()["kind"] == "bollinger_breakout"


def test_create_strategy_rejects_eligible_after_bars_below_warmup(client: TestClient) -> None:
    payload = {
        "name": "Bollinger insufficient warm-up",
        "kind": "bollinger_breakout",
        "parameters": {"period": 20, "num_std_dev": 2, "price_field": "close"},
        "signal_policy": {
            "signal_time": "bar_close",
            "eligible_after_bars": 5,
            "long_only": True,
        },
    }
    response = client.post("/api/v1/strategies", json=payload)

    assert response.status_code == 422
