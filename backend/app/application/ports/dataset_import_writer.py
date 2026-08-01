from typing import Protocol

from app.domain.dataset import DatasetManifest
from app.domain.market_data import DatasetImport, DatasetValidationEvent, NormalizedBar


class DatasetImportWriter(Protocol):
    def persist_accepted_import(
        self,
        *,
        dataset: DatasetManifest,
        bars: list[NormalizedBar],
        import_record: DatasetImport,
        warning_events: list[DatasetValidationEvent],
    ) -> None: ...

    def persist_rejected_import(
        self,
        *,
        import_record: DatasetImport,
        error_event: DatasetValidationEvent,
    ) -> None: ...
