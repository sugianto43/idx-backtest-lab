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


def test_get_dataset_returns_provenance_and_warnings(client: TestClient, monkeypatch: Any) -> None:
    from app.api.routes import datasets as datasets_route

    monkeypatch.setattr(
        datasets_route,
        "fetch_daily_ohlcv_csv",
        lambda ticker, instrument_identifier, start, end: VALID_CSV,
    )
    response = client.post(
        "/api/v1/datasets:import-from-yahoo-finance",
        json={
            "ticker": "BBCA.JK",
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
            "name": "BBCA from Yahoo Finance",
            "instrument_mapping_policy": "ticker_as_of_import",
        },
    )

    assert response.status_code == 201
    dataset_id = response.json()["dataset_id"]

    detail = client.get(f"/api/v1/datasets/{dataset_id}")

    assert detail.status_code == 200
    body = detail.json()
    assert body["source_name"] == "Yahoo Finance"
    assert body["adjustment_policy"] == "split_adjusted"
    assert body["warnings"] == []


def test_get_unknown_dataset_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/datasets/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_list_datasets_paginates(client: TestClient) -> None:
    seed_dataset(get_settings(), name="Dataset A")
    seed_dataset(
        get_settings(),
        name="Dataset B",
        raw_bytes=(
            HEADER
            + "\n2026-02-01,BBCA,200,205,199,204,1000\n2026-02-02,BBCA,204,210,203,209,1500\n"
        ).encode("utf-8"),
    )

    response = client.get("/api/v1/datasets", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["limit"] == 1


def test_list_datasets_includes_row_and_warning_counts(client: TestClient) -> None:
    dataset_id = seed_dataset(get_settings(), raw_bytes=VALID_CSV)

    response = client.get("/api/v1/datasets", params={"limit": 20, "offset": 0})

    assert response.status_code == 200
    item = next(i for i in response.json()["items"] if i["dataset_id"] == dataset_id)
    assert item["row_count"] == 2
    assert item["warning_count"] == 0


def test_import_from_yahoo_finance_creates_dataset_with_fixed_provenance(
    client: TestClient, monkeypatch: Any
) -> None:
    from app.api.routes import datasets as datasets_route

    def fake_fetch(ticker: str, instrument_identifier: str, start: Any, end: Any) -> bytes:
        assert ticker == "BBCA.JK"
        assert instrument_identifier == "BBCA"
        return VALID_CSV

    monkeypatch.setattr(datasets_route, "fetch_daily_ohlcv_csv", fake_fetch)

    response = client.post(
        "/api/v1/datasets:import-from-yahoo-finance",
        json={
            "ticker": "BBCA.JK",
            "instrument_identifier": "BBCA",
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
            "name": "BBCA from Yahoo Finance",
            "instrument_mapping_policy": "ticker_as_of_import",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "valid"
    assert body["dataset_id"] is not None

    detail = client.get(f"/api/v1/datasets/{body['dataset_id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["source_name"] == "Yahoo Finance"
    assert "non-commercial" in detail_body["license_reference"]
    assert detail_body["adjustment_policy"] == "split_adjusted"


def test_import_from_yahoo_finance_fetch_failure_returns_502(
    client: TestClient, monkeypatch: Any
) -> None:
    from app.api.routes import datasets as datasets_route
    from app.infrastructure.market_data.yahoo_finance_provider import YahooFinanceFetchError

    def failing_fetch(ticker: str, instrument_identifier: str, start: Any, end: Any) -> bytes:
        raise YahooFinanceFetchError("no_data", "Yahoo Finance returned no trading bars.")

    monkeypatch.setattr(datasets_route, "fetch_daily_ohlcv_csv", failing_fetch)

    response = client.post(
        "/api/v1/datasets:import-from-yahoo-finance",
        json={
            "ticker": "DOESNOTEXIST",
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
            "name": "Unknown ticker",
            "instrument_mapping_policy": "ticker_as_of_import",
        },
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_fetch_failed"
    assert response.json()["error"]["details"][0]["code"] == "no_data"


def test_import_from_yahoo_finance_duplicate_without_allow_reimport_returns_409(
    client: TestClient, monkeypatch: Any
) -> None:
    from app.api.routes import datasets as datasets_route

    monkeypatch.setattr(
        datasets_route,
        "fetch_daily_ohlcv_csv",
        lambda ticker, instrument_identifier, start, end: VALID_CSV,
    )

    payload = {
        "ticker": "BBCA.JK",
        "start_date": "2026-01-01",
        "end_date": "2026-01-02",
        "name": "BBCA from Yahoo Finance",
        "instrument_mapping_policy": "ticker_as_of_import",
    }
    first = client.post("/api/v1/datasets:import-from-yahoo-finance", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/datasets:import-from-yahoo-finance", json=payload)
    assert second.status_code == 409
