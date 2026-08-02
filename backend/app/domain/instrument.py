from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

ALLOWED_EXCHANGE_CODES = frozenset({"IDX"})


class InstrumentType(StrEnum):
    EQUITY = "equity"


class InstrumentStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"
    UNKNOWN = "unknown"


class AliasConfidence(StrEnum):
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"


class MappingStatus(StrEnum):
    RESOLVED = "resolved"


class InstrumentValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Instrument:
    instrument_id: str
    instrument_type: InstrumentType
    display_name: str
    status: InstrumentStatus
    source_name: str
    created_at_utc: datetime
    currency: str | None = None
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.instrument_id:
            raise InstrumentValidationError("instrument_id must not be empty")
        if not isinstance(self.instrument_type, InstrumentType):
            raise InstrumentValidationError("instrument_type must be an InstrumentType")
        if not self.display_name.strip():
            raise InstrumentValidationError("display_name must not be empty")
        if not isinstance(self.status, InstrumentStatus):
            raise InstrumentValidationError("status must be an InstrumentStatus")
        if not self.source_name.strip():
            raise InstrumentValidationError("source_name must not be empty")
        if self.created_at_utc.tzinfo is None:
            raise InstrumentValidationError("created_at_utc must be timezone-aware")


@dataclass(frozen=True, slots=True)
class InstrumentAlias:
    alias_id: str
    instrument_id: str
    symbol: str
    exchange_code: str
    effective_from: date
    source_name: str
    confidence: AliasConfidence
    created_at_utc: datetime
    effective_to: date | None = None
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.alias_id:
            raise InstrumentValidationError("alias_id must not be empty")
        if not self.instrument_id:
            raise InstrumentValidationError("instrument_id must not be empty")
        if not self.symbol.strip():
            raise InstrumentValidationError("symbol must not be empty")
        if self.exchange_code not in ALLOWED_EXCHANGE_CODES:
            raise InstrumentValidationError(
                f"exchange_code must be one of {sorted(ALLOWED_EXCHANGE_CODES)}"
            )
        if not isinstance(self.confidence, AliasConfidence):
            raise InstrumentValidationError("confidence must be an AliasConfidence")
        if not self.source_name.strip():
            raise InstrumentValidationError("source_name must not be empty")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise InstrumentValidationError("effective_to must not be before effective_from")
        if self.created_at_utc.tzinfo is None:
            raise InstrumentValidationError("created_at_utc must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DatasetInstrumentMapping:
    mapping_id: str
    dataset_id: str
    source_instrument_identifier: str
    instrument_id: str
    effective_from: date
    decision_source: str
    status: MappingStatus
    created_at_utc: datetime
    effective_to: date | None = None

    def __post_init__(self) -> None:
        if not self.mapping_id:
            raise InstrumentValidationError("mapping_id must not be empty")
        if not self.dataset_id:
            raise InstrumentValidationError("dataset_id must not be empty")
        if not self.source_instrument_identifier.strip():
            raise InstrumentValidationError("source_instrument_identifier must not be empty")
        if not self.instrument_id:
            raise InstrumentValidationError("instrument_id must not be empty")
        if not self.decision_source.strip():
            raise InstrumentValidationError("decision_source must not be empty")
        if not isinstance(self.status, MappingStatus):
            raise InstrumentValidationError("status must be a MappingStatus")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise InstrumentValidationError("effective_to must not be before effective_from")
        if self.created_at_utc.tzinfo is None:
            raise InstrumentValidationError("created_at_utc must be timezone-aware")
