from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class CreateBacktestRunRequest(BaseModel):
    strategy_id: str
    strategy_version: int
    dataset_id: str
    instrument_ids: list[str]
    start_date: date
    end_date: date
    capital_amount: str
    capital_currency: str
    position_sizing_fraction: str
    quantity_increment: str
    money_scale: int
    annualization_basis: int
    risk_free_rate: str


class BacktestRunResponse(BaseModel):
    run_id: str
    dataset_id: str
    strategy_id: str | None
    strategy_version: int | None
    schema_version: int | None
    status: str
    manifest_checksum: str | None
    manifest: dict[str, Any]
    warning_count: int
    created_at_utc: datetime


class BacktestRunListResponse(BaseModel):
    items: list[BacktestRunResponse]
    total: int
    limit: int
    offset: int
