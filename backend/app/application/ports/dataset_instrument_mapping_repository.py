from datetime import date
from typing import Protocol

from app.domain.instrument import DatasetInstrumentMapping


class DatasetInstrumentMappingRepository(Protocol):
    def create(self, mapping: DatasetInstrumentMapping) -> DatasetInstrumentMapping: ...

    def list_for_dataset(self, dataset_id: str) -> list[DatasetInstrumentMapping]: ...

    def list_for_instrument(self, instrument_id: str) -> list[DatasetInstrumentMapping]: ...

    def find_overlapping(
        self,
        *,
        dataset_id: str,
        source_instrument_identifier: str,
        effective_from: date,
        effective_to: date | None,
    ) -> list[DatasetInstrumentMapping]: ...
