from typing import Protocol

from app.domain.dataset import DatasetManifest
from app.domain.pagination import Page


class DatasetRepository(Protocol):
    def create(self, dataset: DatasetManifest) -> DatasetManifest: ...

    def get(self, dataset_id: str) -> DatasetManifest | None: ...

    def list(self, *, limit: int, offset: int) -> Page[DatasetManifest]: ...
