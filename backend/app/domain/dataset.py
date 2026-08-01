from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class DatasetValidationStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    WARNING = "warning"
    REJECTED = "rejected"


class InstrumentMappingPolicy(StrEnum):
    PROVIDED_INTERNAL_ID = "provided_internal_id"
    TICKER_AS_OF_IMPORT = "ticker_as_of_import"


class DatasetValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    version: int
    name: str
    source_name: str
    bar_interval: str
    timezone: str
    adjustment_policy: str
    validation_status: DatasetValidationStatus
    created_at_utc: datetime
    source_reference: str | None = None
    license_reference: str | None = None
    content_checksum: str | None = None
    coverage_start_date: date | None = None
    coverage_end_date: date | None = None
    validation_summary: str | None = None
    instrument_mapping_policy: InstrumentMappingPolicy = InstrumentMappingPolicy.TICKER_AS_OF_IMPORT

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise DatasetValidationError("dataset_id must not be empty")
        if self.version < 1:
            raise DatasetValidationError("version must be a positive integer")
        if not self.name.strip():
            raise DatasetValidationError("name must not be empty")
        if not self.source_name.strip():
            raise DatasetValidationError("source_name must not be empty")
        if not self.bar_interval.strip():
            raise DatasetValidationError("bar_interval must not be empty")
        if not self.timezone.strip():
            raise DatasetValidationError("timezone must not be empty")
        if not self.adjustment_policy.strip():
            raise DatasetValidationError("adjustment_policy must not be empty")
        if not isinstance(self.validation_status, DatasetValidationStatus):
            raise DatasetValidationError("validation_status must be a DatasetValidationStatus")
        if not isinstance(self.instrument_mapping_policy, InstrumentMappingPolicy):
            raise DatasetValidationError(
                "instrument_mapping_policy must be an InstrumentMappingPolicy"
            )
        if self.created_at_utc.tzinfo is None:
            raise DatasetValidationError("created_at_utc must be timezone-aware")
        if (
            self.coverage_start_date is not None
            and self.coverage_end_date is not None
            and self.coverage_start_date > self.coverage_end_date
        ):
            raise DatasetValidationError("coverage_start_date must not be after coverage_end_date")
