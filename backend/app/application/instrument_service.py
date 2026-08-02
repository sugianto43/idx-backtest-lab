import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime

from app.application.errors import AliasOverlapError, InstrumentNotFoundError
from app.application.ports.instrument_alias_repository import InstrumentAliasRepository
from app.application.ports.instrument_repository import InstrumentRepository
from app.domain.instrument import (
    AliasConfidence,
    Instrument,
    InstrumentAlias,
    InstrumentStatus,
    InstrumentType,
)


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def _default_clock() -> datetime:
    return datetime.now(UTC)


def create_instrument(
    repository: InstrumentRepository,
    *,
    instrument_type: InstrumentType,
    display_name: str,
    source_name: str,
    status: InstrumentStatus = InstrumentStatus.UNKNOWN,
    currency: str | None = None,
    source_reference: str | None = None,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime] = _default_clock,
) -> Instrument:
    instrument = Instrument(
        instrument_id=id_factory(),
        instrument_type=instrument_type,
        display_name=display_name,
        status=status,
        source_name=source_name,
        currency=currency,
        source_reference=source_reference,
        created_at_utc=clock(),
    )
    return repository.create(instrument)


def add_instrument_alias(
    alias_repository: InstrumentAliasRepository,
    instrument_repository: InstrumentRepository,
    *,
    instrument_id: str,
    symbol: str,
    exchange_code: str,
    effective_from: date,
    source_name: str,
    confidence: AliasConfidence,
    effective_to: date | None = None,
    source_reference: str | None = None,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime] = _default_clock,
) -> InstrumentAlias:
    if instrument_repository.get(instrument_id) is None:
        raise InstrumentNotFoundError(instrument_id)

    overlapping = alias_repository.find_overlapping(
        symbol=symbol,
        exchange_code=exchange_code,
        effective_from=effective_from,
        effective_to=effective_to,
    )
    if overlapping:
        raise AliasOverlapError(symbol, exchange_code)

    alias = InstrumentAlias(
        alias_id=id_factory(),
        instrument_id=instrument_id,
        symbol=symbol,
        exchange_code=exchange_code,
        effective_from=effective_from,
        effective_to=effective_to,
        source_name=source_name,
        source_reference=source_reference,
        confidence=confidence,
        created_at_utc=clock(),
    )
    return alias_repository.create(alias)
