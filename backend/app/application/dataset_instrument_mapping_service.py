import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime

from app.application.errors import (
    DatasetNotFoundError,
    InstrumentNotFoundError,
    MappingOverlapError,
)
from app.application.ports.dataset_instrument_mapping_repository import (
    DatasetInstrumentMappingRepository,
)
from app.application.ports.dataset_repository import DatasetRepository
from app.application.ports.instrument_repository import InstrumentRepository
from app.domain.instrument import DatasetInstrumentMapping, MappingStatus


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def _default_clock() -> datetime:
    return datetime.now(UTC)


def create_dataset_instrument_mapping(
    mapping_repository: DatasetInstrumentMappingRepository,
    dataset_repository: DatasetRepository,
    instrument_repository: InstrumentRepository,
    *,
    dataset_id: str,
    source_instrument_identifier: str,
    instrument_id: str,
    effective_from: date,
    decision_source: str,
    effective_to: date | None = None,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime] = _default_clock,
) -> DatasetInstrumentMapping:
    if dataset_repository.get(dataset_id) is None:
        raise DatasetNotFoundError(dataset_id)
    if instrument_repository.get(instrument_id) is None:
        raise InstrumentNotFoundError(instrument_id)

    overlapping = mapping_repository.find_overlapping(
        dataset_id=dataset_id,
        source_instrument_identifier=source_instrument_identifier,
        effective_from=effective_from,
        effective_to=effective_to,
    )
    if overlapping:
        raise MappingOverlapError(dataset_id, source_instrument_identifier)

    mapping = DatasetInstrumentMapping(
        mapping_id=id_factory(),
        dataset_id=dataset_id,
        source_instrument_identifier=source_instrument_identifier,
        instrument_id=instrument_id,
        effective_from=effective_from,
        effective_to=effective_to,
        decision_source=decision_source,
        status=MappingStatus.RESOLVED,
        created_at_utc=clock(),
    )
    return mapping_repository.create(mapping)
