from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ParsedRow:
    row_number: int
    instrument_identifier: str
    timestamp_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    currency: str | None
    source_row_id: str | None
    zero_volume: bool


@dataclass(frozen=True, slots=True)
class ParsedImport:
    rows: list[ParsedRow]


class CsvParser(Protocol):
    def parse(self, raw_bytes: bytes, *, bar_interval: str, timezone_name: str) -> ParsedImport: ...
