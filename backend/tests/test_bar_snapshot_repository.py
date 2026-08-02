from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import duckdb
import pytest

from app.application.errors import UnresolvedInstrumentMappingError
from app.domain.dataset import DatasetManifest, DatasetValidationStatus, InstrumentMappingPolicy
from app.domain.instrument import (
    DatasetInstrumentMapping,
    Instrument,
    InstrumentStatus,
    InstrumentType,
    MappingStatus,
)
from app.domain.market_data import NormalizedBar
from app.infrastructure.db.bar_snapshot_repository import DuckDBBarSnapshotRepository
from app.infrastructure.db.dataset_instrument_mapping_repository import (
    DuckDBDatasetInstrumentMappingRepository,
)
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.instrument_repository import DuckDBInstrumentRepository
from app.infrastructure.db.migration_runner import run_migrations
from app.infrastructure.settings import Settings

BASE = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    db_path = tmp_path / "test.duckdb"
    connection = duckdb.connect(str(db_path))
    run_migrations(connection)
    connection.close()
    return Settings(database_path=str(db_path))


def _seed(settings: Settings) -> None:
    DuckDBDatasetRepository(settings).create(
        DatasetManifest(
            dataset_id="ds-1",
            version=1,
            name="Sample",
            source_name="manual",
            bar_interval="1d",
            timezone="UTC",
            adjustment_policy="raw",
            validation_status=DatasetValidationStatus.VALID,
            created_at_utc=BASE,
            instrument_mapping_policy=InstrumentMappingPolicy.TICKER_AS_OF_IMPORT,
        )
    )
    DuckDBInstrumentRepository(settings).create(
        Instrument(
            instrument_id="ins-1",
            instrument_type=InstrumentType.EQUITY,
            display_name="Bank Central Asia",
            status=InstrumentStatus.ACTIVE,
            source_name="manual",
            created_at_utc=BASE,
        )
    )
    DuckDBDatasetInstrumentMappingRepository(settings).create(
        DatasetInstrumentMapping(
            mapping_id="map-1",
            dataset_id="ds-1",
            source_instrument_identifier="BBCA",
            instrument_id="ins-1",
            effective_from=date(2020, 1, 1),
            decision_source="manual_review",
            status=MappingStatus.RESOLVED,
            created_at_utc=BASE,
        )
    )

    import duckdb as duckdb_module

    connection = duckdb_module.connect(settings.database_path)
    try:
        for i in range(5):
            close = Decimal(100 + i)
            ts = (BASE + timedelta(days=i)).replace(tzinfo=None)
            connection.execute(
                """
                INSERT INTO normalized_bars (
                    bar_id, dataset_id, source_instrument_identifier, timestamp_utc,
                    bar_interval, open, high, low, close, volume, currency, source_row_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    f"bar-{i}",
                    "ds-1",
                    "BBCA",
                    ts,
                    "1d",
                    close - 1,
                    close + 1,
                    close - 2,
                    close,
                    1000,
                    None,
                    None,
                ],
            )
    finally:
        connection.close()


def test_get_snapshot_returns_bars_in_period(settings: Settings) -> None:
    _seed(settings)
    repository = DuckDBBarSnapshotRepository(settings)

    bars = repository.get_snapshot(
        dataset_id="ds-1",
        instrument_id="ins-1",
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 3),
    )

    assert [b.bar_id for b in bars] == ["bar-1", "bar-2"]
    assert all(isinstance(b, NormalizedBar) for b in bars)


def test_get_snapshot_raises_when_no_mapping_exists(settings: Settings) -> None:
    _seed(settings)
    repository = DuckDBBarSnapshotRepository(settings)

    with pytest.raises(UnresolvedInstrumentMappingError):
        repository.get_snapshot(
            dataset_id="ds-1",
            instrument_id="unmapped-instrument",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
        )


def test_get_snapshot_returns_empty_list_outside_bar_range(settings: Settings) -> None:
    _seed(settings)
    repository = DuckDBBarSnapshotRepository(settings)

    bars = repository.get_snapshot(
        dataset_id="ds-1",
        instrument_id="ins-1",
        start_date=date(2030, 1, 1),
        end_date=date(2030, 1, 5),
    )

    assert bars == []
