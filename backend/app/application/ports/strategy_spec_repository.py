from typing import Protocol

from app.domain.pagination import Page
from app.domain.strategy_spec import StrategySpecV1


class StrategySpecRepository(Protocol):
    def create(self, spec: StrategySpecV1) -> StrategySpecV1: ...

    def get(self, strategy_id: str, version: int) -> StrategySpecV1 | None: ...

    def list(self, *, limit: int, offset: int) -> Page[StrategySpecV1]: ...
