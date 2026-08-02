from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SmaCrossoverParametersSchema(BaseModel):
    fast_window: int
    slow_window: int
    price_field: Literal["close"]


class SignalPolicySchema(BaseModel):
    signal_time: Literal["bar_close"]
    eligible_after_bars: int
    long_only: bool


class CreateStrategyRequest(BaseModel):
    name: str
    kind: Literal["sma_crossover"]
    parameters: SmaCrossoverParametersSchema
    signal_policy: SignalPolicySchema


class StrategySpecResponse(BaseModel):
    strategy_id: str
    version: int
    schema_version: int
    name: str
    kind: str
    parameters: SmaCrossoverParametersSchema
    signal_policy: SignalPolicySchema
    checksum: str
    created_at_utc: datetime


class StrategySpecListResponse(BaseModel):
    items: list[StrategySpecResponse]
    total: int
    limit: int
    offset: int
