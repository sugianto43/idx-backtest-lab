from datetime import date
from typing import Protocol

from app.domain.instrument import InstrumentAlias


class InstrumentAliasRepository(Protocol):
    def create(self, alias: InstrumentAlias) -> InstrumentAlias: ...

    def list_for_instrument(self, instrument_id: str) -> list[InstrumentAlias]: ...

    def find_overlapping(
        self,
        *,
        symbol: str,
        exchange_code: str,
        effective_from: date,
        effective_to: date | None,
    ) -> list[InstrumentAlias]: ...
