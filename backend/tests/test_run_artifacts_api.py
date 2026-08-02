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
    _shared_setup.clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


_shared_setup: dict[str, str] = {}


def _setup_run(client: TestClient, *, import_dataset: bool = True) -> str:
    if import_dataset or not _shared_setup:
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

        _shared_setup.update(
            dataset_id=dataset_id, instrument_id=instrument_id, strategy_id=strategy_id
        )
    else:
        dataset_id = _shared_setup["dataset_id"]
        instrument_id = _shared_setup["instrument_id"]
        strategy_id = _shared_setup["strategy_id"]

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


def _setup_completed_run(client: TestClient) -> str:
    run_id = _setup_run(client)
    execution = client.post(f"/api/v1/backtest-runs/{run_id}:execute")
    assert execution.status_code == 200
    return run_id


def test_run_summary_reports_terminal_status_and_metrics(client: TestClient) -> None:
    run_id = _setup_completed_run(client)

    response = client.get(f"/api/v1/backtest-runs/{run_id}/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["terminal_status"] == "completed"
    assert body["artifact_schema_version"] == 1
    assert body["event_count"] is not None
    metric_keys = {m["metric_key"] for m in body["metrics"]}
    assert metric_keys == {
        "initial_equity",
        "final_equity",
        "total_return",
        "annualized_return",
        "max_drawdown",
        "trade_count",
        "win_rate",
        "realized_pnl",
        "exposure_time_ratio",
    }


def test_run_artifacts_endpoint_returns_bundle_and_provenance(client: TestClient) -> None:
    run_id = _setup_completed_run(client)

    response = client.get(f"/api/v1/backtest-runs/{run_id}/artifacts")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["terminal_status"] == "completed"
    assert body["provenance"]["strategy_id"]
    assert "events" in body["sections"]


def test_events_endpoint_paginates_and_filters_by_type(client: TestClient) -> None:
    run_id = _setup_completed_run(client)

    response = client.get(
        f"/api/v1/backtest-runs/{run_id}/events", params={"type": "fill", "limit": 1, "offset": 0}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "fill"
    assert len(body["items"]) == 1
    assert body["total"] == 2


def test_events_endpoint_rejects_unknown_type(client: TestClient) -> None:
    run_id = _setup_completed_run(client)

    response = client.get(f"/api/v1/backtest-runs/{run_id}/events", params={"type": "not-a-type"})

    assert response.status_code == 422


def test_portfolio_snapshots_endpoint_returns_ordered_snapshots(client: TestClient) -> None:
    run_id = _setup_completed_run(client)

    response = client.get(f"/api/v1/backtest-runs/{run_id}/portfolio-snapshots")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(CLOSES)
    sequences = [item["sequence"] for item in body["items"]]
    assert sequences == sorted(sequences)


def test_reproducibility_manifest_endpoint_returns_canonical_manifest(client: TestClient) -> None:
    run_id = _setup_completed_run(client)

    response = client.get(f"/api/v1/backtest-runs/{run_id}/reproducibility-manifest")

    assert response.status_code == 200
    body = response.json()
    assert body["manifest"]["run_id"] == run_id
    assert body["checksum"]


def test_comparison_compatibility_is_true_for_two_equivalent_runs(client: TestClient) -> None:
    run_id_a = _setup_completed_run(client)
    run_id_b = _setup_run(client, import_dataset=False)
    assert client.post(f"/api/v1/backtest-runs/{run_id_b}:execute").status_code == 200

    response = client.get(
        f"/api/v1/backtest-runs/{run_id_a}/comparison-compatibility",
        params={"other_run_id": run_id_b},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["compatible"] is True
    assert body["reasons"] == []


def test_run_artifacts_endpoint_returns_404_for_unknown_run(client: TestClient) -> None:
    response = client.get("/api/v1/backtest-runs/does-not-exist/artifacts")
    assert response.status_code == 404


def test_summary_before_execution_reports_no_bundle(client: TestClient) -> None:
    run_id = _setup_run(client)

    response = client.get(f"/api/v1/backtest-runs/{run_id}/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "created"
    assert body["terminal_status"] is None
    assert body["artifact_schema_version"] is None
    assert body["metrics"] == []
