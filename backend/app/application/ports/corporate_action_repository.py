from typing import Protocol

from app.domain.corporate_action import CorporateAction
from app.domain.pagination import Page


class CorporateActionRepository(Protocol):
    def create(self, action: CorporateAction) -> CorporateAction: ...

    def get(self, event_id: str) -> CorporateAction | None: ...

    def list_for_instrument(
        self, instrument_id: str, *, limit: int, offset: int
    ) -> Page[CorporateAction]: ...
