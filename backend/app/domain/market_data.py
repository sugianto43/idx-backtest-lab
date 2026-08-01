from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.dataset import DatasetValidationStatus


class MarketDataValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizedBar:
    bar_id: str
    dataset_id: str
    source_instrument_identifier: str
    timestamp_utc: datetime
    bar_interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    currency: str | None = None
    source_row_id: str | None = None

    def __post_init__(self) -> None:
        if not self.bar_id:
            raise MarketDataValidationError("bar_id must not be empty")
        if not self.dataset_id:
            raise MarketDataValidationError("dataset_id must not be empty")
        if not self.source_instrument_identifier.strip():
            raise MarketDataValidationError("source_instrument_identifier must not be empty")
        if not self.bar_interval.strip():
            raise MarketDataValidationError("bar_interval must not be empty")
        if self.timestamp_utc.tzinfo is None:
            raise MarketDataValidationError("timestamp_utc must be timezone-aware")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise MarketDataValidationError("OHLC values must be strictly positive")
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise MarketDataValidationError("OHLC values violate low <= open,close <= high")
        if self.volume < 0:
            raise MarketDataValidationError("volume must not be negative")


class ValidationSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class DatasetValidationEvent:
    event_id: str
    import_id: str
    severity: ValidationSeverity
    code: str
    message: str
    created_at_utc: datetime
    dataset_id: str | None = None
    source_row_number: int | None = None

    def __post_init__(self) -> None:
        if not self.event_id:
            raise MarketDataValidationError("event_id must not be empty")
        if not self.import_id:
            raise MarketDataValidationError("import_id must not be empty")
        if not isinstance(self.severity, ValidationSeverity):
            raise MarketDataValidationError("severity must be a ValidationSeverity")
        if not self.code.strip():
            raise MarketDataValidationError("code must not be empty")
        if not self.message.strip():
            raise MarketDataValidationError("message must not be empty")
        if self.created_at_utc.tzinfo is None:
            raise MarketDataValidationError("created_at_utc must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DatasetImport:
    import_id: str
    raw_filename: str
    content_checksum: str
    byte_size: int
    requested_metadata_json: str
    status: DatasetValidationStatus
    row_count: int
    accepted_row_count: int
    warning_count: int
    error_count: int
    started_at_utc: datetime
    finished_at_utc: datetime
    dataset_id: str | None = None
    failure_code: str | None = None
    failure_row_number: int | None = None

    def __post_init__(self) -> None:
        if not self.import_id:
            raise MarketDataValidationError("import_id must not be empty")
        if not self.raw_filename.strip():
            raise MarketDataValidationError("raw_filename must not be empty")
        if not self.content_checksum.strip():
            raise MarketDataValidationError("content_checksum must not be empty")
        if self.byte_size < 0:
            raise MarketDataValidationError("byte_size must not be negative")
        if not isinstance(self.status, DatasetValidationStatus):
            raise MarketDataValidationError("status must be a DatasetValidationStatus")
        for label, value in (
            ("row_count", self.row_count),
            ("accepted_row_count", self.accepted_row_count),
            ("warning_count", self.warning_count),
            ("error_count", self.error_count),
        ):
            if value < 0:
                raise MarketDataValidationError(f"{label} must not be negative")
        if self.started_at_utc.tzinfo is None:
            raise MarketDataValidationError("started_at_utc must be timezone-aware")
        if self.finished_at_utc.tzinfo is None:
            raise MarketDataValidationError("finished_at_utc must be timezone-aware")
        if self.finished_at_utc < self.started_at_utc:
            raise MarketDataValidationError("finished_at_utc must not be before started_at_utc")
