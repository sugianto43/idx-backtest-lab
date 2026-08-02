from typing import Protocol

from app.domain.instrument import Instrument
from app.domain.pagination import Page


class InstrumentRepository(Protocol):
    def create(self, instrument: Instrument) -> Instrument: ...

    def get(self, instrument_id: str) -> Instrument | None: ...

    def list(self, *, limit: int, offset: int) -> Page[Instrument]: ...
