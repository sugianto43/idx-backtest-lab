from datetime import date
from typing import Protocol

from app.domain.market_data import NormalizedBar


class BarSnapshotRepository(Protocol):
    def get_snapshot(
        self, *, dataset_id: str, instrument_id: str, start_date: date, end_date: date
    ) -> list[NormalizedBar]: ...
