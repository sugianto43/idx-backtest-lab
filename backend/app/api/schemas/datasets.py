from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.domain.dataset import InstrumentMappingPolicy


class DatasetImportResponse(BaseModel):
    import_id: str
    dataset_id: str | None
    status: Literal["valid", "warning"]
    row_count: int
    accepted_row_count: int
    warning_count: int
    started_at_utc: datetime
    finished_at_utc: datetime


class DatasetWarning(BaseModel):
    code: str
    message: str
    source_row_number: int | None
    created_at_utc: datetime


class DatasetSummary(BaseModel):
    dataset_id: str
    name: str
    source_name: str
    source_reference: str | None
    license_reference: str | None
    bar_interval: str
    timezone: str
    adjustment_policy: str
    instrument_mapping_policy: InstrumentMappingPolicy
    coverage_start_date: date | None
    coverage_end_date: date | None
    validation_status: str
    validation_summary: str | None
    created_at_utc: datetime


class DatasetDetailResponse(DatasetSummary):
    row_count: int
    warning_count: int
    warnings: list[DatasetWarning]


class DatasetListResponse(BaseModel):
    items: list[DatasetSummary]
    total: int
    limit: int
    offset: int
