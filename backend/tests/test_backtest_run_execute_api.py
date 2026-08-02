from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.settings import get_settings
from app.main import create_app
from tests.conftest import seed_dataset

HEADER = "timestamp,instrument_identifier,open,high,low,close,volume"
CLOSES = [10, 9, 8, 12, 16, 20, 8, 4, 2, 2]


def _csv_bytes() -> bytes:
    lines = [HEADER]
    for i, close in enumerate(CLOSES):
        open_ = close - 0.5
        day = i + 1
        lines.append(f"2026-01-{day:02d},BBCA,{open_},{close + 1},{close - 1},{close},1000")
    return ("\n".join(lines) + "\n").encode("utf-8")


STRATEGY_PAYLOAD = {
    "name": "SMA crossover 2/3",
    "kind": "sma_crossover",
    "parameters": {"fast_window": 2, "slow_window": 3, "price_field": "close"},
    "signal_policy": {"signal_time": "bar_close", "eligible_after_bars": 3, "long_only": True},
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


def _setup_run(client: TestClient) -> str:
    dataset_id = seed_dataset(get_settings(), raw_bytes=_csv_bytes())

    instrument = client.post(
        "/api/v1/instruments",
        json={
            "instrument_type": "equity",
            "display_name": "Bank Central Asia",
            "source_name": "manual",
        },
    )
    assert instrument.status_code == 201
    instrument_id = instrument.json()["instrument_id"]

    mapping = client.post(
        f"/api/v1/datasets/{dataset_id}/instrument-mappings",
        json={
            "source_instrument_identifier": "BBCA",
            "instrument_id": instrument_id,
            "effective_from": "2026-01-01",
            "decision_source": "manual_review",
        },
    )
    assert mapping.status_code == 201

    strategy = client.post("/api/v1/strategies", json=STRATEGY_PAYLOAD)
    assert strategy.status_code == 201
    strategy_id = strategy.json()["strategy_id"]

    run = client.post(
        "/api/v1/backtest-runs",
        json={
            "strategy_id": strategy_id,
            "strategy_version": 1,
            "dataset_id": dataset_id,
            "instrument_ids": [instrument_id],
            "start_date": "2026-01-01",
            "end_date": f"2026-01-{len(CLOSES):02d}",
            "capital_amount": "1000000.00",
            "capital_currency": "IDR",
            "position_sizing_fraction": "0.50",
            "quantity_increment": "1",
            "money_scale": 2,
            "annualization_basis": 252,
            "risk_free_rate": "0.00",
        },
    )
    assert run.status_code == 201
    run_id: str = run.json()["run_id"]
    return run_id


def test_execute_backtest_run_returns_completed_summary(client: TestClient) -> None:
    run_id = _setup_run(client)

    response = client.post(f"/api/v1/backtest-runs/{run_id}:execute")

    assert response.status_code == 200
    body = response.json()
    assert body["terminal_status"] == "completed"
    assert body["status"] == "completed"
    assert body["order_count"] == 2
    assert body["fill_count"] == 2
    assert "interim" in body["note"].lower()


def test_get_run_after_execution_reflects_completed_status(client: TestClient) -> None:
    run_id = _setup_run(client)
    client.post(f"/api/v1/backtest-runs/{run_id}:execute")

    response = client.get(f"/api/v1/backtest-runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_execute_unknown_run_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/backtest-runs/does-not-exist:execute")
    assert response.status_code == 404


def test_execute_run_twice_returns_409_on_second_call(client: TestClient) -> None:
    run_id = _setup_run(client)
    first = client.post(f"/api/v1/backtest-runs/{run_id}:execute")
    assert first.status_code == 200

    second = client.post(f"/api/v1/backtest-runs/{run_id}:execute")

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


def test_execute_run_with_unmapped_universe_returns_422(client: TestClient) -> None:
    dataset_id = seed_dataset(get_settings(), raw_bytes=_csv_bytes())

    instrument = client.post(
        "/api/v1/instruments",
        json={
            "instrument_type": "equity",
            "display_name": "Unmapped Co",
            "source_name": "manual",
        },
    )
    instrument_id = instrument.json()["instrument_id"]
    # Deliberately skip creating a dataset-instrument-mapping.

    strategy = client.post("/api/v1/strategies", json=STRATEGY_PAYLOAD)
    strategy_id = strategy.json()["strategy_id"]

    run = client.post(
        "/api/v1/backtest-runs",
        json={
            "strategy_id": strategy_id,
            "strategy_version": 1,
            "dataset_id": dataset_id,
            "instrument_ids": [instrument_id],
            "start_date": "2026-01-01",
            "end_date": f"2026-01-{len(CLOSES):02d}",
            "capital_amount": "1000000.00",
            "capital_currency": "IDR",
            "position_sizing_fraction": "0.50",
            "quantity_increment": "1",
            "money_scale": 2,
            "annualization_basis": 252,
            "risk_free_rate": "0.00",
        },
    )
    run_id = run.json()["run_id"]

    response = client.post(f"/api/v1/backtest-runs/{run_id}:execute")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
