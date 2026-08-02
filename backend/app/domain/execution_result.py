from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(StrEnum):
    FILLED = "filled"
    REJECTED = "rejected"


class TerminalStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OrderEvent:
    order_id: str
    instrument_id: str
    side: OrderSide
    created_at_utc: datetime
    intended_quantity: int
    status: OrderStatus
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class FillEvent:
    order_id: str
    instrument_id: str
    side: OrderSide
    filled_at_utc: datetime
    quantity: int
    price: Decimal
    currency: str
    commission: Decimal
    tax: Decimal
    slippage: Decimal


@dataclass(frozen=True, slots=True)
class PositionEvent:
    timestamp_utc: datetime
    instrument_id: str
    quantity: int
    average_cost: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class CashEvent:
    timestamp_utc: datetime
    currency: str
    cash_before: Decimal
    cash_after: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class ExecutionWarning:
    code: str
    message: str
    instrument_id: str | None = None
    timestamp_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class ExecutionMetadata:
    adapter_name: str
    adapter_version: str
    manifest_checksum: str
    dataset_checksum: str
    ordering_policy: str
    started_at_utc: datetime
    finished_at_utc: datetime
    event_count: int


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    metadata: ExecutionMetadata
    order_events: tuple[OrderEvent, ...]
    fill_events: tuple[FillEvent, ...]
    position_events: tuple[PositionEvent, ...]
    cash_events: tuple[CashEvent, ...]
    warnings: tuple[ExecutionWarning, ...]
    terminal_status: TerminalStatus
    failure_code: str | None = None
