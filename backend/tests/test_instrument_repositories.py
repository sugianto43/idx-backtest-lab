from datetime import UTC, date, datetime
from typing import Any

import duckdb
import pytest

from app.domain.corporate_action import (
    CorporateAction,
    CorporateActionStatus,
    CorporateActionType,
)
from app.domain.dataset import DatasetManifest, DatasetValidationStatus
from app.domain.instrument import (
    AliasConfidence,
    DatasetInstrumentMapping,
    Instrument,
    InstrumentAlias,
    InstrumentStatus,
    InstrumentType,
    MappingStatus,
)
from app.infrastructure.db.corporate_action_repository import DuckDBCorporateActionRepository
from app.infrastructure.db.dataset_instrument_mapping_repository import (
    DuckDBDatasetInstrumentMappingRepository,
)
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.instrument_alias_repository import DuckDBInstrumentAliasRepository
from app.infrastructure.db.instrument_repository import DuckDBInstrumentRepository
from app.infrastructure.db.migration_runner import run_migrations
from app.infrastructure.settings import Settings


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    db_path = tmp_path / "test.duckdb"
    connection = duckdb.connect(str(db_path))
    run_migrations(connection)
    connection.close()
    return Settings(database_path=str(db_path))


def _instrument(**overrides: Any) -> Instrument:
    defaults: dict[str, Any] = {
        "instrument_id": "ins-1",
        "instrument_type": InstrumentType.EQUITY,
        "display_name": "Bank Central Asia",
        "status": InstrumentStatus.ACTIVE,
        "source_name": "manual",
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return Instrument(**defaults)


def test_instrument_create_and_get_round_trip(settings: Settings) -> None:
    repository = DuckDBInstrumentRepository(settings)
    instrument = _instrument()

    repository.create(instrument)

    assert repository.get("ins-1") == instrument
    assert repository.get("does-not-exist") is None


def test_instrument_list_paginates(settings: Settings) -> None:
    repository = DuckDBInstrumentRepository(settings)
    for i in range(3):
        repository.create(
            _instrument(
                instrument_id=f"ins-{i}", created_at_utc=datetime(2026, 1, i + 1, tzinfo=UTC)
            )
        )

    page = repository.list(limit=2, offset=0)

    assert page.total == 3
    assert [item.instrument_id for item in page.items] == ["ins-0", "ins-1"]


def _alias(**overrides: Any) -> InstrumentAlias:
    defaults: dict[str, Any] = {
        "alias_id": "alias-1",
        "instrument_id": "ins-1",
        "symbol": "BBCA",
        "exchange_code": "IDX",
        "effective_from": date(2020, 1, 1),
        "source_name": "manual",
        "confidence": AliasConfidence.CONFIRMED,
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return InstrumentAlias(**defaults)


def test_alias_create_and_list_for_instrument(settings: Settings) -> None:
    instrument_repository = DuckDBInstrumentRepository(settings)
    instrument_repository.create(_instrument())
    alias_repository = DuckDBInstrumentAliasRepository(settings)

    alias_repository.create(_alias())

    aliases = alias_repository.list_for_instrument("ins-1")
    assert len(aliases) == 1
    assert aliases[0].symbol == "BBCA"


def test_alias_find_overlapping_detects_overlap(settings: Settings) -> None:
    instrument_repository = DuckDBInstrumentRepository(settings)
    instrument_repository.create(_instrument())
    alias_repository = DuckDBInstrumentAliasRepository(settings)
    alias_repository.create(
        _alias(effective_from=date(2020, 1, 1), effective_to=date(2020, 12, 31))
    )

    overlapping = alias_repository.find_overlapping(
        symbol="BBCA",
        exchange_code="IDX",
        effective_from=date(2020, 6, 1),
        effective_to=None,
    )
    assert len(overlapping) == 1

    non_overlapping = alias_repository.find_overlapping(
        symbol="BBCA",
        exchange_code="IDX",
        effective_from=date(2021, 1, 1),
        effective_to=None,
    )
    assert non_overlapping == []


def test_alias_rejects_unknown_instrument_fk(settings: Settings) -> None:
    alias_repository = DuckDBInstrumentAliasRepository(settings)
    with pytest.raises(duckdb.ConstraintException):
        alias_repository.create(_alias(instrument_id="does-not-exist"))


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
    }
    defaults.update(overrides)
    return DatasetManifest(**defaults)


def _mapping(**overrides: Any) -> DatasetInstrumentMapping:
    defaults: dict[str, Any] = {
        "mapping_id": "map-1",
        "dataset_id": "ds-1",
        "source_instrument_identifier": "BBCA",
        "instrument_id": "ins-1",
        "effective_from": date(2020, 1, 1),
        "decision_source": "manual_review",
        "status": MappingStatus.RESOLVED,
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DatasetInstrumentMapping(**defaults)


def test_mapping_create_and_list(settings: Settings) -> None:
    DuckDBDatasetRepository(settings).create(_dataset())
    DuckDBInstrumentRepository(settings).create(_instrument())
    mapping_repository = DuckDBDatasetInstrumentMappingRepository(settings)

    mapping_repository.create(_mapping())

    assert len(mapping_repository.list_for_dataset("ds-1")) == 1
    assert len(mapping_repository.list_for_instrument("ins-1")) == 1


def test_mapping_find_overlapping(settings: Settings) -> None:
    DuckDBDatasetRepository(settings).create(_dataset())
    DuckDBInstrumentRepository(settings).create(_instrument())
    mapping_repository = DuckDBDatasetInstrumentMappingRepository(settings)
    mapping_repository.create(
        _mapping(effective_from=date(2020, 1, 1), effective_to=date(2020, 12, 31))
    )

    overlapping = mapping_repository.find_overlapping(
        dataset_id="ds-1",
        source_instrument_identifier="BBCA",
        effective_from=date(2020, 6, 1),
        effective_to=None,
    )
    assert len(overlapping) == 1


def _action(**overrides: Any) -> CorporateAction:
    defaults: dict[str, Any] = {
        "event_id": "evt-1",
        "instrument_id": "ins-1",
        "event_type": CorporateActionType.CASH_DIVIDEND,
        "effective_date": date(2026, 1, 1),
        "status": CorporateActionStatus.REPORTED,
        "source_name": "manual",
        "payload_json": '{"amount_per_share": "150"}',
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return CorporateAction(**defaults)


def test_corporate_action_create_get_list(settings: Settings) -> None:
    DuckDBInstrumentRepository(settings).create(_instrument())
    repository = DuckDBCorporateActionRepository(settings)

    repository.create(_action())

    assert repository.get("evt-1") is not None
    page = repository.list_for_instrument("ins-1", limit=10, offset=0)
    assert page.total == 1


def test_corporate_action_supersede_retains_both(settings: Settings) -> None:
    DuckDBInstrumentRepository(settings).create(_instrument())
    repository = DuckDBCorporateActionRepository(settings)
    repository.create(_action())

    repository.create(
        _action(
            event_id="evt-2",
            payload_json='{"amount_per_share": "175"}',
            supersedes_event_id="evt-1",
        )
    )

    page = repository.list_for_instrument("ins-1", limit=10, offset=0)
    assert page.total == 2
    assert {item.event_id for item in page.items} == {"evt-1", "evt-2"}


def test_corporate_action_rejects_unknown_instrument_fk(settings: Settings) -> None:
    repository = DuckDBCorporateActionRepository(settings)
    with pytest.raises(duckdb.ConstraintException):
        repository.create(_action(instrument_id="does-not-exist"))
