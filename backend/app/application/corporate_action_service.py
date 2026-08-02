import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime

from app.application.errors import CorporateActionNotFoundError, InstrumentNotFoundError
from app.application.ports.corporate_action_repository import CorporateActionRepository
from app.application.ports.instrument_repository import InstrumentRepository
from app.domain.corporate_action import (
    CorporateAction,
    CorporateActionStatus,
    CorporateActionType,
)


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def _default_clock() -> datetime:
    return datetime.now(UTC)


def record_corporate_action(
    action_repository: CorporateActionRepository,
    instrument_repository: InstrumentRepository,
    *,
    instrument_id: str,
    event_type: CorporateActionType,
    effective_date: date,
    source_name: str,
    payload_json: str,
    status: CorporateActionStatus = CorporateActionStatus.REPORTED,
    announcement_date: date | None = None,
    source_reference: str | None = None,
    supersedes_event_id: str | None = None,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime] = _default_clock,
) -> CorporateAction:
    if instrument_repository.get(instrument_id) is None:
        raise InstrumentNotFoundError(instrument_id)

    if supersedes_event_id is not None:
        superseded = action_repository.get(supersedes_event_id)
        if superseded is None:
            raise CorporateActionNotFoundError(supersedes_event_id)

    action = CorporateAction(
        event_id=id_factory(),
        instrument_id=instrument_id,
        event_type=event_type,
        effective_date=effective_date,
        announcement_date=announcement_date,
        status=status,
        source_name=source_name,
        source_reference=source_reference,
        payload_json=payload_json,
        supersedes_event_id=supersedes_event_id,
        created_at_utc=clock(),
    )
    return action_repository.create(action)
