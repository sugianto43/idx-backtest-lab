from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.dataset import DatasetValidationStatus
from app.domain.market_data import (
    DatasetImport,
    DatasetValidationEvent,
    MarketDataValidationError,
    NormalizedBar,
    ValidationSeverity,
)


def _bar(**overrides: object) -> NormalizedBar:
    defaults: dict[str, object] = {
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
    return NormalizedBar(**defaults)  # type: ignore[arg-type]


def test_valid_bar_constructs() -> None:
    bar = _bar()
    assert bar.open == Decimal("100")


def test_bar_rejects_non_positive_price() -> None:
    with pytest.raises(MarketDataValidationError):
        _bar(open=Decimal("0"))


def test_bar_rejects_ohlc_violation() -> None:
    with pytest.raises(MarketDataValidationError):
        _bar(high=Decimal("50"))


def test_bar_rejects_negative_volume() -> None:
    with pytest.raises(MarketDataValidationError):
        _bar(volume=-1)


def test_bar_rejects_naive_timestamp() -> None:
    with pytest.raises(MarketDataValidationError):
        _bar(timestamp_utc=datetime(2026, 1, 1))


def _event(**overrides: object) -> DatasetValidationEvent:
    defaults: dict[str, object] = {
        "event_id": "evt-1",
        "import_id": "imp-1",
        "severity": ValidationSeverity.WARNING,
        "code": "zero_volume_bars",
        "message": "1 row has zero volume.",
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DatasetValidationEvent(**defaults)  # type: ignore[arg-type]


def test_valid_event_constructs() -> None:
    assert _event().code == "zero_volume_bars"


def test_event_rejects_empty_code() -> None:
    with pytest.raises(MarketDataValidationError):
        _event(code="")


def test_event_rejects_invalid_severity() -> None:
    with pytest.raises(MarketDataValidationError):
        _event(severity="warning")


def _import_record(**overrides: object) -> DatasetImport:
    defaults: dict[str, object] = {
        "import_id": "imp-1",
        "raw_filename": "upload.csv",
        "content_checksum": "abc123",
        "byte_size": 100,
        "requested_metadata_json": "{}",
        "status": DatasetValidationStatus.VALID,
        "row_count": 1,
        "accepted_row_count": 1,
        "warning_count": 0,
        "error_count": 0,
        "started_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "finished_at_utc": datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DatasetImport(**defaults)  # type: ignore[arg-type]


def test_valid_import_record_constructs() -> None:
    assert _import_record().status == DatasetValidationStatus.VALID


def test_import_record_rejects_negative_counts() -> None:
    with pytest.raises(MarketDataValidationError):
        _import_record(warning_count=-1)


def test_import_record_rejects_finished_before_started() -> None:
    with pytest.raises(MarketDataValidationError):
        _import_record(
            started_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at_utc=datetime(2025, 12, 31, tzinfo=UTC),
        )
