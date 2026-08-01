from datetime import UTC, datetime
from typing import Any

import duckdb
import pytest

from app.domain.dataset import DatasetManifest, DatasetValidationError, DatasetValidationStatus
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.migration_runner import run_migrations
from app.infrastructure.settings import Settings


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    db_path = tmp_path / "test.duckdb"
    connection = duckdb.connect(str(db_path))
    run_migrations(connection)
    connection.close()
    return Settings(database_path=str(db_path))


def _manifest(**overrides: Any) -> DatasetManifest:
    defaults: dict[str, Any] = {
        "dataset_id": "ds-1",
        "version": 1,
        "name": "Sample dataset",
        "source_name": "synthetic-test",
        "bar_interval": "1d",
        "timezone": "UTC",
        "adjustment_policy": "unknown",
        "validation_status": DatasetValidationStatus.VALID,
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DatasetManifest(**defaults)


def test_create_and_get_round_trip(settings: Settings) -> None:
    repository = DuckDBDatasetRepository(settings)
    manifest = _manifest()

    repository.create(manifest)
    fetched = repository.get("ds-1")

    assert fetched == manifest


def test_get_returns_none_for_unknown_id(settings: Settings) -> None:
    repository = DuckDBDatasetRepository(settings)

    assert repository.get("does-not-exist") is None


def test_list_paginates_and_orders_by_creation(settings: Settings) -> None:
    repository = DuckDBDatasetRepository(settings)
    repository.create(_manifest(dataset_id="ds-1", created_at_utc=datetime(2026, 1, 1, tzinfo=UTC)))
    repository.create(_manifest(dataset_id="ds-2", created_at_utc=datetime(2026, 1, 2, tzinfo=UTC)))
    repository.create(_manifest(dataset_id="ds-3", created_at_utc=datetime(2026, 1, 3, tzinfo=UTC)))

    page = repository.list(limit=2, offset=0)

    assert page.total == 3
    assert [item.dataset_id for item in page.items] == ["ds-1", "ds-2"]


def test_domain_rejects_missing_required_field() -> None:
    with pytest.raises(DatasetValidationError):
        _manifest(name="   ")


def test_domain_rejects_invalid_status() -> None:
    with pytest.raises(ValueError):
        _manifest(validation_status="not-a-status")


def test_domain_rejects_invalid_coverage_range() -> None:
    with pytest.raises(DatasetValidationError):
        _manifest(
            coverage_start_date=datetime(2026, 1, 2, tzinfo=UTC).date(),
            coverage_end_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
        )
