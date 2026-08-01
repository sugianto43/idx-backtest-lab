from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.settings import get_settings
from app.main import create_app

HEADER = "timestamp,instrument_identifier,open,high,low,close,volume"

VALID_CSV = (
    HEADER + "\n2026-01-01,BBCA,100,105,99,104,1000\n2026-01-02,BBCA,104,110,103,109,1500\n"
).encode("utf-8")

MALFORMED_CSV = (
    b"timestamp,instrument_identifier,open,high,low,close\n2026-01-01,BBCA,100,105,99,104\n"
)

DEFAULT_METADATA = {
    "name": "Sample dataset",
    "source_name": "Manual export",
    "license_reference": "user_supplied_unknown",
    "bar_interval": "1d",
    "timezone": "UTC",
    "adjustment_policy": "raw",
    "instrument_mapping_policy": "ticker_as_of_import",
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


def _import(client: TestClient, *, csv_bytes: bytes = VALID_CSV, **metadata_overrides: str) -> Any:
    metadata = {**DEFAULT_METADATA, **metadata_overrides}
    return client.post(
        "/api/v1/datasets:import",
        files={"file": ("prices.csv", csv_bytes, "text/csv")},
        data=metadata,
    )


def test_valid_import_returns_201_with_dataset_id(client: TestClient) -> None:
    response = _import(client)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "valid"
    assert body["dataset_id"]
    assert body["row_count"] == 2


def test_unknown_adjustment_policy_returns_warning_status(client: TestClient) -> None:
    response = _import(client, adjustment_policy="unknown")

    assert response.status_code == 201
    assert response.json()["status"] == "warning"


def test_malformed_csv_returns_422_validation_error(client: TestClient) -> None:
    response = _import(client, csv_bytes=MALFORMED_CSV)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["code"] == "invalid_header"
    assert body["error"]["correlation_id"]


def test_duplicate_import_without_allow_reimport_returns_409(client: TestClient) -> None:
    first = _import(client)
    assert first.status_code == 201

    second = _import(client)

    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "conflict"
    assert body["error"]["details"][0]["existing_dataset_id"] == first.json()["dataset_id"]


def test_allow_reimport_creates_a_new_dataset_version(client: TestClient) -> None:
    first = _import(client)
    second = _import(client, allow_reimport="true")

    assert second.status_code == 201
    assert second.json()["dataset_id"] != first.json()["dataset_id"]


def test_get_dataset_returns_provenance_and_warnings(client: TestClient) -> None:
    imported = _import(client, adjustment_policy="unknown").json()

    response = client.get(f"/api/v1/datasets/{imported['dataset_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "warning"
    assert body["adjustment_policy"] == "unknown"
    assert any(warning["code"] == "unknown_adjustment_policy" for warning in body["warnings"])


def test_get_unknown_dataset_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/datasets/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_list_datasets_paginates(client: TestClient) -> None:
    _import(client)
    _import(client, allow_reimport="true")

    response = client.get("/api/v1/datasets", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["limit"] == 1
