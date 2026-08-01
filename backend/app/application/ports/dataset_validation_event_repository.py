from typing import Protocol

from app.domain.market_data import DatasetValidationEvent
from app.domain.pagination import Page


class DatasetValidationEventRepository(Protocol):
    def list_for_dataset(
        self, dataset_id: str, *, limit: int, offset: int
    ) -> Page[DatasetValidationEvent]: ...
