import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BacktestRunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS: dict[BacktestRunStatus, frozenset[BacktestRunStatus]] = {
    BacktestRunStatus.CREATED: frozenset({BacktestRunStatus.RUNNING, BacktestRunStatus.CANCELLED}),
    BacktestRunStatus.RUNNING: frozenset({BacktestRunStatus.COMPLETED, BacktestRunStatus.FAILED}),
    BacktestRunStatus.COMPLETED: frozenset(),
    BacktestRunStatus.FAILED: frozenset(),
    BacktestRunStatus.CANCELLED: frozenset(),
}


def is_transition_allowed(current: BacktestRunStatus, next_status: BacktestRunStatus) -> bool:
    return next_status in _ALLOWED_TRANSITIONS[current]


class RunManifestValidationError(ValueError):
    pass


def _require_non_empty(value: str, field: str) -> None:
    if not value.strip():
        raise RunManifestValidationError(f"{field} must not be empty")


def _require_timezone_aware(value: datetime | None, field: str) -> None:
    if value is not None and value.tzinfo is None:
        raise RunManifestValidationError(f"{field} must be timezone-aware")


def _require_valid_json(value: str) -> None:
    try:
        json.loads(value)
    except json.JSONDecodeError as exc:
        raise RunManifestValidationError("configuration_json must be valid JSON") from exc


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_id: str
    dataset_id: str
    strategy_spec_version: str
    engine_version: str
    configuration_json: str
    status: BacktestRunStatus
    created_at_utc: datetime
    warning_count: int = 0
    started_at_utc: datetime | None = None
    finished_at_utc: datetime | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        self._validate_identity()
        self._validate_status_and_payload()
        self._validate_temporal_fields()

    def _validate_identity(self) -> None:
        if not self.run_id:
            raise RunManifestValidationError("run_id must not be empty")
        if not self.dataset_id:
            raise RunManifestValidationError("dataset_id must not be empty")
        _require_non_empty(self.strategy_spec_version, "strategy_spec_version")
        _require_non_empty(self.engine_version, "engine_version")

    def _validate_status_and_payload(self) -> None:
        if not isinstance(self.status, BacktestRunStatus):
            raise RunManifestValidationError("status must be a BacktestRunStatus")
        _require_valid_json(self.configuration_json)
        if self.warning_count < 0:
            raise RunManifestValidationError("warning_count must not be negative")

    def _validate_temporal_fields(self) -> None:
        _require_timezone_aware(self.created_at_utc, "created_at_utc")
        _require_timezone_aware(self.started_at_utc, "started_at_utc")
        _require_timezone_aware(self.finished_at_utc, "finished_at_utc")
        if self.started_at_utc is not None and self.started_at_utc < self.created_at_utc:
            raise RunManifestValidationError("started_at_utc must not be before created_at_utc")
        if (
            self.finished_at_utc is not None
            and self.started_at_utc is not None
            and self.finished_at_utc < self.started_at_utc
        ):
            raise RunManifestValidationError("finished_at_utc must not be before started_at_utc")
