from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.domain.corporate_action import (
    CorporateAction,
    CorporateActionStatus,
    CorporateActionType,
    CorporateActionValidationError,
)


def _action(**overrides: Any) -> CorporateAction:
    defaults: dict[str, Any] = {
        "event_id": "evt-1",
        "instrument_id": "ins-1",
        "event_type": CorporateActionType.CASH_DIVIDEND,
        "effective_date": date(2026, 1, 1),
        "status": CorporateActionStatus.REPORTED,
        "source_name": "manual",
        "payload_json": '{"amount_per_share": "150", "currency": "IDR"}',
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return CorporateAction(**defaults)


def test_valid_action_constructs() -> None:
    assert _action().event_type == CorporateActionType.CASH_DIVIDEND


def test_action_rejects_invalid_event_type() -> None:
    with pytest.raises(CorporateActionValidationError):
        _action(event_type="cash_dividend")


def test_action_rejects_invalid_status() -> None:
    with pytest.raises(CorporateActionValidationError):
        _action(status="reported")


def test_action_rejects_invalid_payload_json() -> None:
    with pytest.raises(CorporateActionValidationError):
        _action(payload_json="not-json")


def test_action_rejects_naive_created_at() -> None:
    with pytest.raises(CorporateActionValidationError):
        _action(created_at_utc=datetime(2026, 1, 1))
