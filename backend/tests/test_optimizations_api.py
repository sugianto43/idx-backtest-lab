from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.settings import get_settings
from app.main import create_app
from tests.conftest import seed_dataset

HEADER = "timestamp,instrument_identifier,open,high,low,close,volume"

# Train (days 1-10): mild oscillation. Validation (days 11-20): strong uptrend, tempting for a
# long-only crossover. Holdout (days 21-30): sharp downturn -- demonstrates that a candidate
# selected purely on validation performance is not protected from reversal on unseen data.
TRAIN_CLOSES = [10, 11, 9, 10, 12, 9, 11, 10, 12, 9]
VALIDATION_CLOSES = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
HOLDOUT_CLOSES = [28, 24, 20, 16, 12, 10, 8, 6, 5, 4]
ALL_CLOSES = TRAIN_CLOSES + VALIDATION_CLOSES + HOLDOUT_CLOSES


def _csv_bytes() -> bytes:
    lines = [HEADER]
    for i, close in enumerate(ALL_CLOSES):
        day = i + 1
        open_ = close - 0.5
        lines.append(f"2026-01-{day:02d},BBCA,{open_},{close + 1},{close - 1},{close},1000")
    return ("\n".join(lines) + "\n").encode("utf-8")


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


def _setup_dataset_and_instrument(client: TestClient) -> tuple[str, str]:
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
    return dataset_id, instrument_id


def _optimization_payload(dataset_id: str, instrument_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "dataset_id": dataset_id,
        "instrument_id": instrument_id,
        "base_strategy_name": "SMA crossover grid",
        "fast_windows": [2, 3],
        "slow_windows": [4, 5],
        "train_start": "2026-01-01",
        "train_end": "2026-01-10",
        "validation_start": "2026-01-11",
        "validation_end": "2026-01-20",
        "holdout_start": "2026-01-21",
        "holdout_end": "2026-01-30",
        "capital_amount": "1000000.00",
        "capital_currency": "IDR",
        "position_sizing_fraction": "0.50",
        "quantity_increment": "1",
        "money_scale": 2,
        "annualization_basis": 252,
        "risk_free_rate": "0.00",
        "objective_metric_key": "total_return",
    }
    payload.update(overrides)
    return payload


def test_create_optimization_expands_grid_deterministically(client: TestClient) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)

    response = client.post(
        "/api/v1/optimizations", json=_optimization_payload(dataset_id, instrument_id)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "created"
    assert body["candidate_count"] == 4
    assert body["rejected_count"] == 0
    assert body["checksum"].startswith("sha256:")
    assert body["fast_window_grid"] == [2, 3]
    assert body["slow_window_grid"] == [4, 5]
    assert body["holdout"] == {
        "sealed": True,
        "run_id": None,
        "objective_status": None,
        "objective_value": None,
        "objective_reason": None,
    }
    assert body["selected_candidate_id"] is None

    optimization_id = body["optimization_id"]
    candidates = client.get(f"/api/v1/optimizations/{optimization_id}/candidates").json()
    assert candidates["total"] == 4
    assert [item["fast_window"] for item in candidates["items"]] == [2, 2, 3, 3]
    assert [item["slow_window"] for item in candidates["items"]] == [4, 5, 4, 5]
    assert all(item["status"] == "pending" for item in candidates["items"])


def test_create_optimization_records_rejected_invalid_pairs(client: TestClient) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)

    response = client.post(
        "/api/v1/optimizations",
        json=_optimization_payload(
            dataset_id, instrument_id, fast_windows=[2, 6], slow_windows=[4]
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["candidate_count"] == 1
    assert body["rejected_count"] == 1

    candidates = client.get(f"/api/v1/optimizations/{body['optimization_id']}/candidates").json()
    rejected = next(item for item in candidates["items"] if item["status"] == "rejected")
    assert rejected["fast_window"] == 6
    assert rejected["slow_window"] == 4
    assert rejected["rejection_reason"] == "fast_window must be less than slow_window"


def test_create_optimization_rejects_overlapping_partitions(client: TestClient) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)

    response = client.post(
        "/api/v1/optimizations",
        json=_optimization_payload(dataset_id, instrument_id, validation_start="2026-01-05"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["code"] == "invalid_partitions"


def test_create_optimization_rejects_unsupported_objective(client: TestClient) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)

    response = client.post(
        "/api/v1/optimizations",
        json=_optimization_payload(dataset_id, instrument_id, objective_metric_key="sharpe_ratio"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["code"] == "unsupported_objective"


def test_create_optimization_rejects_oversized_grid(client: TestClient) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)

    response = client.post(
        "/api/v1/optimizations",
        json=_optimization_payload(
            dataset_id,
            instrument_id,
            fast_windows=list(range(1, 20)),
            slow_windows=list(range(20, 25)),
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["code"] == "candidate_grid_too_large"


def test_create_optimization_rejects_insufficient_partition_coverage(client: TestClient) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)

    response = client.post(
        "/api/v1/optimizations",
        json=_optimization_payload(dataset_id, instrument_id, slow_windows=[20]),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["code"] == "insufficient_partition_coverage"


def test_execute_optimization_completes_and_seals_holdout_until_terminal(
    client: TestClient,
) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)
    created = client.post(
        "/api/v1/optimizations", json=_optimization_payload(dataset_id, instrument_id)
    ).json()
    optimization_id = created["optimization_id"]

    response = client.post(f"/api/v1/optimizations/{optimization_id}:execute")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["selected_candidate_id"] is not None
    assert body["selection_reason"] == "highest total_return"
    assert body["selection_audit"] is not None
    assert len(body["selection_audit"]) == 4
    assert body["holdout"]["sealed"] is False
    assert body["holdout"]["run_id"] is not None

    candidates = client.get(f"/api/v1/optimizations/{optimization_id}/candidates").json()
    assert candidates["total"] == 4
    for item in candidates["items"]:
        assert item["status"] in ("completed", "failed")
        assert item["train_run_id"] is not None
        if item["status"] == "failed":
            assert item["objective_status"] == "not_available"
            assert item["objective_reason"] in ("train_run_failed", "validation_run_failed")
        else:
            assert item["validation_run_id"] is not None
            assert item["objective_status"] in ("available", "not_available")

    available_values = [
        item["objective_value"]
        for item in candidates["items"]
        if item["objective_status"] == "available"
    ]
    assert available_values, "expected at least one candidate with an available objective"

    selected = client.get(f"/api/v1/optimizations/{optimization_id}").json()
    selected_candidate = next(
        item
        for item in candidates["items"]
        if item["candidate_id"] == selected["selected_candidate_id"]
    )
    assert selected_candidate["objective_status"] == "available"
    assert all(
        Decimal(selected_candidate["objective_value"]) >= Decimal(other)
        for other in available_values
    )


def test_optimization_before_execution_reports_pending_candidates_and_sealed_holdout(
    client: TestClient,
) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)
    created = client.post(
        "/api/v1/optimizations", json=_optimization_payload(dataset_id, instrument_id)
    ).json()

    detail = client.get(f"/api/v1/optimizations/{created['optimization_id']}").json()

    assert detail["status"] == "created"
    assert detail["holdout"]["sealed"] is True
    assert detail["selection_audit"] is None


def test_execute_optimization_twice_returns_409(client: TestClient) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)
    created = client.post(
        "/api/v1/optimizations", json=_optimization_payload(dataset_id, instrument_id)
    ).json()
    optimization_id = created["optimization_id"]

    first = client.post(f"/api/v1/optimizations/{optimization_id}:execute")
    assert first.status_code == 200

    second = client.post(f"/api/v1/optimizations/{optimization_id}:execute")
    assert second.status_code == 409


def test_execute_unknown_optimization_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/optimizations/does-not-exist:execute")
    assert response.status_code == 404


def test_list_optimizations_paginates(client: TestClient) -> None:
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)
    client.post("/api/v1/optimizations", json=_optimization_payload(dataset_id, instrument_id))

    response = client.get("/api/v1/optimizations", params={"limit": 10, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "created"


def test_holdout_is_evaluated_independently_of_validation_selection(client: TestClient) -> None:
    """Synthetic fixture per the bias-safeguard test plan: the validation window is a strong
    uptrend (tempting for a long-only crossover) and the holdout window immediately reverses.
    Selection happens purely on the validation objective; the holdout run is a genuinely
    separate, independently executed backtest (its own run ID, its own artifact/metrics) --
    never a copy or re-derivation of the validation result. The API must report holdout
    honestly rather than implying validation performance predicts it.
    """
    dataset_id, instrument_id = _setup_dataset_and_instrument(client)
    created = client.post(
        "/api/v1/optimizations", json=_optimization_payload(dataset_id, instrument_id)
    ).json()
    optimization_id = created["optimization_id"]

    client.post(f"/api/v1/optimizations/{optimization_id}:execute")
    detail = client.get(f"/api/v1/optimizations/{optimization_id}").json()
    candidates = client.get(f"/api/v1/optimizations/{optimization_id}/candidates").json()

    selected_candidate = next(
        item
        for item in candidates["items"]
        if item["candidate_id"] == detail["selected_candidate_id"]
    )

    assert selected_candidate["objective_status"] == "available"
    assert detail["holdout"]["objective_status"] in ("available", "not_available")
    assert detail["holdout"]["run_id"] != selected_candidate["validation_run_id"]
    assert detail["holdout"]["run_id"] != selected_candidate["train_run_id"]
