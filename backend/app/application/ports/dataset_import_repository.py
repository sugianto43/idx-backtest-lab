from typing import Protocol

from app.domain.market_data import DatasetImport


class DatasetImportRepository(Protocol):
    def get(self, import_id: str) -> DatasetImport | None: ...

    def find_by_content_checksum(self, content_checksum: str) -> DatasetImport | None: ...

    def get_latest_for_dataset(self, dataset_id: str) -> DatasetImport | None: ...
