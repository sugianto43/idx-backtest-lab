from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.domain.instrument import (
    AliasConfidence,
    DatasetInstrumentMapping,
    Instrument,
    InstrumentAlias,
    InstrumentStatus,
    InstrumentType,
    InstrumentValidationError,
    MappingStatus,
)


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


def test_valid_instrument_constructs() -> None:
    assert _instrument().status == InstrumentStatus.ACTIVE


def test_instrument_rejects_empty_display_name() -> None:
    with pytest.raises(InstrumentValidationError):
        _instrument(display_name="  ")


def test_instrument_rejects_invalid_type() -> None:
    with pytest.raises(InstrumentValidationError):
        _instrument(instrument_type="equity")


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


def test_valid_alias_constructs() -> None:
    assert _alias().symbol == "BBCA"


def test_alias_rejects_unsupported_exchange() -> None:
    with pytest.raises(InstrumentValidationError):
        _alias(exchange_code="NYSE")


def test_alias_rejects_effective_to_before_effective_from() -> None:
    with pytest.raises(InstrumentValidationError):
        _alias(effective_from=date(2020, 6, 1), effective_to=date(2020, 1, 1))


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


def test_valid_mapping_constructs() -> None:
    assert _mapping().status == MappingStatus.RESOLVED


def test_mapping_rejects_empty_decision_source() -> None:
    with pytest.raises(InstrumentValidationError):
        _mapping(decision_source="  ")


def test_mapping_rejects_effective_to_before_effective_from() -> None:
    with pytest.raises(InstrumentValidationError):
        _mapping(effective_from=date(2020, 6, 1), effective_to=date(2020, 1, 1))
