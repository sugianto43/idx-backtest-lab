import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class CorporateActionType(StrEnum):
    CASH_DIVIDEND = "cash_dividend"
    STOCK_DIVIDEND = "stock_dividend"
    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    RIGHTS_ISSUE = "rights_issue"
    TICKER_CHANGE = "ticker_change"
    DELISTING = "delisting"
    OTHER = "other"


class CorporateActionStatus(StrEnum):
    REPORTED = "reported"
    VERIFIED = "verified"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class CorporateActionValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CorporateAction:
    event_id: str
    instrument_id: str
    event_type: CorporateActionType
    effective_date: date
    status: CorporateActionStatus
    source_name: str
    payload_json: str
    created_at_utc: datetime
    announcement_date: date | None = None
    source_reference: str | None = None
    supersedes_event_id: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id:
            raise CorporateActionValidationError("event_id must not be empty")
        if not self.instrument_id:
            raise CorporateActionValidationError("instrument_id must not be empty")
        if not isinstance(self.event_type, CorporateActionType):
            raise CorporateActionValidationError("event_type must be a CorporateActionType")
        if not isinstance(self.status, CorporateActionStatus):
            raise CorporateActionValidationError("status must be a CorporateActionStatus")
        if not self.source_name.strip():
            raise CorporateActionValidationError("source_name must not be empty")
        try:
            json.loads(self.payload_json)
        except json.JSONDecodeError as exc:
            raise CorporateActionValidationError("payload_json must be valid JSON") from exc
        if self.created_at_utc.tzinfo is None:
            raise CorporateActionValidationError("created_at_utc must be timezone-aware")
