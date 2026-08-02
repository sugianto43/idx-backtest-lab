from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from app.domain.corporate_action import CorporateActionStatus, CorporateActionType
from app.domain.instrument import AliasConfidence, InstrumentStatus, InstrumentType


class CreateInstrumentRequest(BaseModel):
    instrument_type: InstrumentType
    display_name: str
    source_name: str
    status: InstrumentStatus = InstrumentStatus.UNKNOWN
    currency: str | None = None
    source_reference: str | None = None


class InstrumentResponse(BaseModel):
    instrument_id: str
    instrument_type: InstrumentType
    display_name: str
    currency: str | None
    status: InstrumentStatus
    source_name: str
    source_reference: str | None
    created_at_utc: datetime


class AddAliasRequest(BaseModel):
    symbol: str
    exchange_code: str
    effective_from: date
    source_name: str
    confidence: AliasConfidence
    effective_to: date | None = None
    source_reference: str | None = None


class AliasResponse(BaseModel):
    alias_id: str
    instrument_id: str
    symbol: str
    exchange_code: str
    effective_from: date
    effective_to: date | None
    source_name: str
    source_reference: str | None
    confidence: AliasConfidence
    created_at_utc: datetime


class MappingSummary(BaseModel):
    mapping_id: str
    dataset_id: str
    source_instrument_identifier: str
    effective_from: date
    effective_to: date | None


class InstrumentDetailResponse(InstrumentResponse):
    aliases: list[AliasResponse]
    mappings: list[MappingSummary]
    corporate_action_count: int


class InstrumentListResponse(BaseModel):
    items: list[InstrumentResponse]
    total: int
    limit: int
    offset: int


class CreateMappingRequest(BaseModel):
    source_instrument_identifier: str
    instrument_id: str
    effective_from: date
    decision_source: str
    effective_to: date | None = None


class MappingResponse(BaseModel):
    mapping_id: str
    dataset_id: str
    source_instrument_identifier: str
    instrument_id: str
    effective_from: date
    effective_to: date | None
    decision_source: str
    status: str
    created_at_utc: datetime


class DatasetMappingListResponse(BaseModel):
    items: list[MappingResponse]


class RecordCorporateActionRequest(BaseModel):
    event_type: CorporateActionType
    effective_date: date
    source_name: str
    payload: dict[str, Any]
    status: CorporateActionStatus = CorporateActionStatus.REPORTED
    announcement_date: date | None = None
    source_reference: str | None = None
    supersedes_event_id: str | None = None


class CorporateActionResponse(BaseModel):
    event_id: str
    instrument_id: str
    event_type: CorporateActionType
    effective_date: date
    announcement_date: date | None
    status: CorporateActionStatus
    source_name: str
    source_reference: str | None
    payload: dict[str, Any]
    supersedes_event_id: str | None
    created_at_utc: datetime


class CorporateActionListResponse(BaseModel):
    items: list[CorporateActionResponse]
    total: int
    limit: int
    offset: int
