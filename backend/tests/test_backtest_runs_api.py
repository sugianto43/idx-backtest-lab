from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.settings import get_settings
from app.main import create_app

HEADER = "timestamp,instrument_identifier,open,high,low,close,volume"
VALID_CSV = (
    HEADER + "\n2020-01-01,BBCA,100,105,99,104,1000\n2020-01-02,BBCA,104,110,103,109,1500\n"
).encode("utf-8")

DATASET_METADATA = {
    "name": "Sample dataset",
    "source_name": "Manual export",
    "license_reference": "user_supplied_unknown",
    "bar_interval": "1d",
    "timezone": "UTC",
    "adjustment_policy": "raw",
    "instrument_mapping_policy": "ticker_as_of_import",
}

STRATEGY_PAYLOAD = {
    "name": "SMA crossover 10/30",
    "kind": "sma_crossover",
    "parameters": {"fast_window": 10, "slow_window": 30, "price_field": "close"},
    "signal_policy": {"signal_time": "bar_close", "eligible_after_bars": 30, "long_only": True},
}


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


def _setup_dataset(client: TestClient) -> str:
    response = client.post(
        "/api/v1/datasets:import",
        files={"file": ("prices.csv", VALID_CSV, "text/csv")},
        data=DATASET_METADATA,
    )
    assert response.status_code == 201
    dataset_id: str = response.json()["dataset_id"]
    return dataset_id


def _setup_instrument(client: TestClient) -> str:
    response = client.post(
        "/api/v1/instruments",
        json={
            "instrument_type": "equity",
            "display_name": "Bank Central Asia",
            "source_name": "manual",
        },
    )
    assert response.status_code == 201
    instrument_id: str = response.json()["instrument_id"]
    return instrument_id


def _setup_strategy(client: TestClient) -> str:
    response = client.post("/api/v1/strategies", json=STRATEGY_PAYLOAD)
    assert response.status_code == 201
    strategy_id: str = response.json()["strategy_id"]
    return strategy_id


def _run_payload(
    strategy_id: str, dataset_id: str, instrument_id: str, **overrides: Any
) -> dict[str, Any]:
    payload = {
        "strategy_id": strategy_id,
        "strategy_version": 1,
        "dataset_id": dataset_id,
        "instrument_ids": [instrument_id],
        "start_date": "2020-01-01",
        "end_date": "2020-01-02",
        "capital_amount": "100000000.00",
        "capital_currency": "IDR",
        "position_sizing_fraction": "1.00",
        "quantity_increment": "1",
        "money_scale": 2,
        "annualization_basis": 252,
        "risk_free_rate": "0.00",
    }
    payload.update(overrides)
    return payload


def test_create_backtest_run_returns_201(client: TestClient) -> None:
    dataset_id = _setup_dataset(client)
    instrument_id = _setup_instrument(client)
    strategy_id = _setup_strategy(client)

    response = client.post(
        "/api/v1/backtest-runs", json=_run_payload(strategy_id, dataset_id, instrument_id)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "created"
    assert body["manifest_checksum"].startswith("sha256:")
    assert body["manifest"]["universe"]["instrument_ids"] == [instrument_id]


def test_create_backtest_run_unknown_strategy_returns_404(client: TestClient) -> None:
    dataset_id = _setup_dataset(client)
    instrument_id = _setup_instrument(client)

    response = client.post(
        "/api/v1/backtest-runs",
        json=_run_payload("does-not-exist", dataset_id, instrument_id),
    )

    assert response.status_code == 404


def test_create_backtest_run_unknown_dataset_returns_404(client: TestClient) -> None:
    instrument_id = _setup_instrument(client)
    strategy_id = _setup_strategy(client)

    response = client.post(
        "/api/v1/backtest-runs",
        json=_run_payload(strategy_id, "does-not-exist", instrument_id),
    )

    assert response.status_code == 404


def test_create_backtest_run_period_outside_coverage_returns_422(client: TestClient) -> None:
    dataset_id = _setup_dataset(client)
    instrument_id = _setup_instrument(client)
    strategy_id = _setup_strategy(client)

    response = client.post(
        "/api/v1/backtest-runs",
        json=_run_payload(strategy_id, dataset_id, instrument_id, end_date="2025-01-01"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_get_backtest_run_round_trip(client: TestClient) -> None:
    dataset_id = _setup_dataset(client)
    instrument_id = _setup_instrument(client)
    strategy_id = _setup_strategy(client)
    created = client.post(
        "/api/v1/backtest-runs", json=_run_payload(strategy_id, dataset_id, instrument_id)
    ).json()

    response = client.get(f"/api/v1/backtest-runs/{created['run_id']}")

    assert response.status_code == 200
    assert response.json()["manifest_checksum"] == created["manifest_checksum"]


def test_get_unknown_backtest_run_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/backtest-runs/does-not-exist")
    assert response.status_code == 404


def test_list_backtest_runs_paginates(client: TestClient) -> None:
    dataset_id = _setup_dataset(client)
    instrument_id = _setup_instrument(client)
    strategy_id = _setup_strategy(client)
    client.post("/api/v1/backtest-runs", json=_run_payload(strategy_id, dataset_id, instrument_id))

    response = client.get("/api/v1/backtest-runs", params={"limit": 10, "offset": 0})

    assert response.status_code == 200
    assert response.json()["total"] == 1
