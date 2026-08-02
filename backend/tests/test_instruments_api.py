from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.settings import get_settings
from app.main import create_app
from tests.conftest import seed_dataset

HEADER = "timestamp,instrument_identifier,open,high,low,close,volume"
VALID_CSV = (
    HEADER + "\n2026-01-01,BBCA,100,105,99,104,1000\n2026-01-02,BBCA,104,110,103,109,1500\n"
).encode("utf-8")


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


def _create_instrument(client: TestClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "instrument_type": "equity",
        "display_name": "Bank Central Asia",
        "source_name": "manual",
        **overrides,
    }
    response = client.post("/api/v1/instruments", json=payload)
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


def _create_dataset(client: TestClient) -> str:
    return seed_dataset(get_settings(), raw_bytes=VALID_CSV)


def test_create_and_get_instrument(client: TestClient) -> None:
    created = _create_instrument(client)

    response = client.get(f"/api/v1/instruments/{created['instrument_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Bank Central Asia"
    assert body["aliases"] == []
    assert body["corporate_action_count"] == 0


def test_get_unknown_instrument_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/instruments/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_list_instruments_paginates(client: TestClient) -> None:
    _create_instrument(client, display_name="A")
    _create_instrument(client, display_name="B")

    response = client.get("/api/v1/instruments", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1


def test_add_alias_success(client: TestClient) -> None:
    instrument = _create_instrument(client)

    response = client.post(
        f"/api/v1/instruments/{instrument['instrument_id']}/aliases",
        json={
            "symbol": "BBCA",
            "exchange_code": "IDX",
            "effective_from": "2020-01-01",
            "source_name": "manual",
            "confidence": "confirmed",
        },
    )

    assert response.status_code == 201
    assert response.json()["symbol"] == "BBCA"


def test_add_alias_unknown_instrument_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/instruments/does-not-exist/aliases",
        json={
            "symbol": "BBCA",
            "exchange_code": "IDX",
            "effective_from": "2020-01-01",
            "source_name": "manual",
            "confidence": "confirmed",
        },
    )
    assert response.status_code == 404


def test_add_overlapping_alias_returns_409(client: TestClient) -> None:
    instrument_a = _create_instrument(client, display_name="A")
    instrument_b = _create_instrument(client, display_name="B")
    alias_payload = {
        "symbol": "BBCA",
        "exchange_code": "IDX",
        "effective_from": "2020-01-01",
        "source_name": "manual",
        "confidence": "confirmed",
    }
    ok = client.post(
        f"/api/v1/instruments/{instrument_a['instrument_id']}/aliases", json=alias_payload
    )
    assert ok.status_code == 201

    conflict = client.post(
        f"/api/v1/instruments/{instrument_b['instrument_id']}/aliases", json=alias_payload
    )

    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"


def test_create_instrument_mapping_success(client: TestClient) -> None:
    dataset_id = _create_dataset(client)
    instrument = _create_instrument(client)

    response = client.post(
        f"/api/v1/datasets/{dataset_id}/instrument-mappings",
        json={
            "source_instrument_identifier": "BBCA",
            "instrument_id": instrument["instrument_id"],
            "effective_from": "2026-01-01",
            "decision_source": "manual_review",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "resolved"


def test_create_mapping_unknown_dataset_returns_404(client: TestClient) -> None:
    instrument = _create_instrument(client)
    response = client.post(
        "/api/v1/datasets/does-not-exist/instrument-mappings",
        json={
            "source_instrument_identifier": "BBCA",
            "instrument_id": instrument["instrument_id"],
            "effective_from": "2026-01-01",
            "decision_source": "manual_review",
        },
    )
    assert response.status_code == 404


def test_create_overlapping_mapping_returns_409(client: TestClient) -> None:
    dataset_id = _create_dataset(client)
    instrument = _create_instrument(client)
    payload = {
        "source_instrument_identifier": "BBCA",
        "instrument_id": instrument["instrument_id"],
        "effective_from": "2026-01-01",
        "decision_source": "manual_review",
    }
    ok = client.post(f"/api/v1/datasets/{dataset_id}/instrument-mappings", json=payload)
    assert ok.status_code == 201

    conflict = client.post(f"/api/v1/datasets/{dataset_id}/instrument-mappings", json=payload)
    assert conflict.status_code == 409


def test_record_corporate_action_and_list(client: TestClient) -> None:
    instrument = _create_instrument(client)

    response = client.post(
        f"/api/v1/instruments/{instrument['instrument_id']}/corporate-actions",
        json={
            "event_type": "cash_dividend",
            "effective_date": "2026-01-01",
            "source_name": "manual",
            "payload": {"amount_per_share": "150", "currency": "IDR"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["payload"]["amount_per_share"] == "150"

    listing = client.get(f"/api/v1/instruments/{instrument['instrument_id']}/corporate-actions")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_record_corporate_action_unknown_instrument_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/instruments/does-not-exist/corporate-actions",
        json={
            "event_type": "cash_dividend",
            "effective_date": "2026-01-01",
            "source_name": "manual",
            "payload": {},
        },
    )
    assert response.status_code == 404


def test_supersede_corporate_action(client: TestClient) -> None:
    instrument = _create_instrument(client)
    first = client.post(
        f"/api/v1/instruments/{instrument['instrument_id']}/corporate-actions",
        json={
            "event_type": "cash_dividend",
            "effective_date": "2026-01-01",
            "source_name": "manual",
            "payload": {"amount_per_share": "150"},
        },
    ).json()

    second = client.post(
        f"/api/v1/instruments/{instrument['instrument_id']}/corporate-actions",
        json={
            "event_type": "cash_dividend",
            "effective_date": "2026-01-01",
            "source_name": "manual",
            "payload": {"amount_per_share": "175"},
            "supersedes_event_id": first["event_id"],
        },
    )

    assert second.status_code == 201
    listing = client.get(f"/api/v1/instruments/{instrument['instrument_id']}/corporate-actions")
    assert listing.json()["total"] == 2
