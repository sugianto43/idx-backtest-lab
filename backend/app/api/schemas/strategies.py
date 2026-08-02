from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class SignalPolicySchema(BaseModel):
    signal_time: Literal["bar_close"]
    eligible_after_bars: int
    long_only: bool


class CreateStrategyRequest(BaseModel):
    name: str
    kind: str
    parameters: dict[str, Any]
    signal_policy: SignalPolicySchema


class StrategySpecResponse(BaseModel):
    strategy_id: str
    version: int
    schema_version: int
    name: str
    kind: str
    parameters: dict[str, Any]
    signal_policy: SignalPolicySchema
    checksum: str
    created_at_utc: datetime


class StrategySpecListResponse(BaseModel):
    items: list[StrategySpecResponse]
    total: int
    limit: int
    offset: int
