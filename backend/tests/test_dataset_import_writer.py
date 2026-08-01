from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import duckdb
import pytest

from app.domain.dataset import DatasetManifest, DatasetValidationStatus, InstrumentMappingPolicy
from app.domain.market_data import (
    DatasetImport,
    DatasetValidationEvent,
    NormalizedBar,
    ValidationSeverity,
)
from app.infrastructure.db.dataset_import_writer import DuckDBDatasetImportWriter
from app.infrastructure.db.migration_runner import run_migrations
from app.infrastructure.settings import Settings


def _scalar(connection: Any, sql: str, params: list[Any] | None = None) -> Any:
    row = connection.execute(sql, params or [])
    fetched = row.fetchone()
    assert fetched is not None
    return fetched[0]


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    db_path = tmp_path / "test.duckdb"
    connection = duckdb.connect(str(db_path))
    run_migrations(connection)
    connection.close()
    return Settings(database_path=str(db_path))


def _dataset(**overrides: Any) -> DatasetManifest:
    defaults: dict[str, Any] = {
        "dataset_id": "ds-1",
        "version": 1,
        "name": "Sample",
        "source_name": "Manual export",
        "bar_interval": "1d",
        "timezone": "UTC",
        "adjustment_policy": "raw",
        "validation_status": DatasetValidationStatus.VALID,
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "instrument_mapping_policy": InstrumentMappingPolicy.TICKER_AS_OF_IMPORT,
    }
    defaults.update(overrides)
    return DatasetManifest(**defaults)


def _bar(**overrides: Any) -> NormalizedBar:
    defaults: dict[str, Any] = {
        "bar_id": "bar-1",
        "dataset_id": "ds-1",
        "source_instrument_identifier": "BBCA",
        "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "bar_interval": "1d",
        "open": Decimal("100"),
        "high": Decimal("105"),
        "low": Decimal("99"),
        "close": Decimal("104"),
        "volume": 1000,
    }
    defaults.update(overrides)
    return NormalizedBar(**defaults)


def _import_record(**overrides: Any) -> DatasetImport:
    defaults: dict[str, Any] = {
        "import_id": "imp-1",
        "dataset_id": "ds-1",
        "raw_filename": "prices.csv",
        "content_checksum": "checksum-1",
        "byte_size": 100,
        "requested_metadata_json": "{}",
        "status": DatasetValidationStatus.VALID,
        "row_count": 1,
        "accepted_row_count": 1,
        "warning_count": 0,
        "error_count": 0,
        "started_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "finished_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DatasetImport(**defaults)


def test_persist_accepted_import_writes_all_tables(settings: Settings) -> None:
    writer = DuckDBDatasetImportWriter(settings)

    writer.persist_accepted_import(
        dataset=_dataset(),
        bars=[_bar()],
        import_record=_import_record(),
        warning_events=[],
    )

    connection = duckdb.connect(settings.database_path)
    try:
        assert _scalar(connection, "SELECT COUNT(*) FROM datasets") == 1
        assert _scalar(connection, "SELECT COUNT(*) FROM normalized_bars") == 1
        assert _scalar(connection, "SELECT COUNT(*) FROM dataset_imports") == 1
    finally:
        connection.close()


def test_persist_accepted_import_with_warning_events(settings: Settings) -> None:
    writer = DuckDBDatasetImportWriter(settings)
    warning = DatasetValidationEvent(
        event_id="evt-1",
        import_id="imp-1",
        dataset_id="ds-1",
        severity=ValidationSeverity.WARNING,
        code="zero_volume_bars",
        message="1 row has zero volume.",
        created_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )

    writer.persist_accepted_import(
        dataset=_dataset(validation_status=DatasetValidationStatus.WARNING),
        bars=[_bar()],
        import_record=_import_record(status=DatasetValidationStatus.WARNING, warning_count=1),
        warning_events=[warning],
    )

    connection = duckdb.connect(settings.database_path)
    try:
        count = _scalar(
            connection,
            "SELECT COUNT(*) FROM dataset_validation_events WHERE dataset_id = ?",
            ["ds-1"],
        )
        assert count == 1
    finally:
        connection.close()


def test_persist_accepted_import_rolls_back_on_duplicate_dataset_id(settings: Settings) -> None:
    writer = DuckDBDatasetImportWriter(settings)
    writer.persist_accepted_import(
        dataset=_dataset(),
        bars=[_bar()],
        import_record=_import_record(),
        warning_events=[],
    )

    with pytest.raises(duckdb.ConstraintException):
        writer.persist_accepted_import(
            dataset=_dataset(),  # same dataset_id -> primary key violation
            bars=[_bar(bar_id="bar-2")],
            import_record=_import_record(import_id="imp-2"),
            warning_events=[],
        )

    connection = duckdb.connect(settings.database_path)
    try:
        assert _scalar(connection, "SELECT COUNT(*) FROM normalized_bars") == 1
        assert _scalar(connection, "SELECT COUNT(*) FROM dataset_imports") == 1
    finally:
        connection.close()


def test_persist_rejected_import_writes_import_and_error_event(settings: Settings) -> None:
    writer = DuckDBDatasetImportWriter(settings)
    error_event = DatasetValidationEvent(
        event_id="evt-1",
        import_id="imp-1",
        dataset_id=None,
        severity=ValidationSeverity.ERROR,
        code="invalid_header",
        message="bad header",
        created_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )

    writer.persist_rejected_import(
        import_record=_import_record(
            dataset_id=None,
            status=DatasetValidationStatus.REJECTED,
            row_count=0,
            accepted_row_count=0,
            error_count=1,
            failure_code="invalid_header",
        ),
        error_event=error_event,
    )

    connection = duckdb.connect(settings.database_path)
    try:
        assert _scalar(connection, "SELECT COUNT(*) FROM datasets") == 0
        row = connection.execute(
            "SELECT status, failure_code FROM dataset_imports WHERE import_id = 'imp-1'"
        ).fetchone()
        assert row == ("rejected", "invalid_header")
        assert _scalar(connection, "SELECT COUNT(*) FROM dataset_validation_events") == 1
    finally:
        connection.close()
