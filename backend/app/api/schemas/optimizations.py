from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class CreateOptimizationRequest(BaseModel):
    dataset_id: str
    instrument_id: str
    base_strategy_name: str
    fast_windows: list[int]
    slow_windows: list[int]
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    holdout_start: date
    holdout_end: date
    capital_amount: str
    capital_currency: str
    position_sizing_fraction: str
    quantity_increment: str
    money_scale: int
    annualization_basis: int
    risk_free_rate: str
    objective_metric_key: str


class CandidateSummaryResponse(BaseModel):
    candidate_id: str
    sequence: int
    fast_window: int
    slow_window: int
    status: str
    rejection_reason: str | None
    strategy_id: str | None
    strategy_version: int | None
    train_run_id: str | None
    validation_run_id: str | None
    objective_status: str | None
    objective_value: str | None
    objective_reason: str | None
    warning_count: int
    created_at_utc: datetime


class HoldoutResultResponse(BaseModel):
    sealed: bool
    run_id: str | None = None
    objective_status: str | None = None
    objective_value: str | None = None
    objective_reason: str | None = None


class OptimizationSummaryResponse(BaseModel):
    optimization_id: str
    status: str
    dataset_id: str
    instrument_id: str
    base_strategy_name: str
    objective_metric_key: str
    candidate_count: int
    rejected_count: int
    max_candidate_count: int
    failure_code: str | None
    created_at_utc: datetime
    started_at_utc: datetime | None
    finished_at_utc: datetime | None


class OptimizationDetailResponse(OptimizationSummaryResponse):
    schema_version: int
    checksum: str
    fast_window_grid: list[int]
    slow_window_grid: list[int]
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    holdout_start: date
    holdout_end: date
    tie_break_rule: str
    manifest: dict[str, Any]
    selected_candidate_id: str | None
    selection_reason: str | None
    selection_audit: list[dict[str, Any]] | None
    selected_at_utc: datetime | None
    holdout: HoldoutResultResponse


class OptimizationListResponse(BaseModel):
    items: list[OptimizationSummaryResponse]
    total: int
    limit: int
    offset: int


class OptimizationCandidatesResponse(BaseModel):
    items: list[CandidateSummaryResponse]
    total: int
    limit: int
    offset: int
