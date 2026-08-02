from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

OPTIMIZATION_SCHEMA_VERSION = 1
TIE_BREAK_RULE = (
    "highest_objective_value_then_lower_slow_window_then_lower_fast_window_then_candidate_id"
)

ALLOWED_OBJECTIVE_METRICS = frozenset(
    {
        "initial_equity",
        "final_equity",
        "total_return",
        "annualized_return",
        "max_drawdown",
        "trade_count",
        "win_rate",
        "realized_pnl",
        "exposure_time_ratio",
    }
)


class OptimizationStatus(StrEnum):
    CREATED = "created"
    VALIDATING = "validating"
    RUNNING_TRAIN_VALIDATION = "running_train_validation"
    SELECTING = "selecting"
    RUNNING_HOLDOUT = "running_holdout"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_ALLOWED_TRANSITIONS: dict[OptimizationStatus, frozenset[OptimizationStatus]] = {
    OptimizationStatus.CREATED: frozenset(
        {OptimizationStatus.VALIDATING, OptimizationStatus.CANCELLED, OptimizationStatus.FAILED}
    ),
    OptimizationStatus.VALIDATING: frozenset(
        {OptimizationStatus.RUNNING_TRAIN_VALIDATION, OptimizationStatus.FAILED}
    ),
    OptimizationStatus.RUNNING_TRAIN_VALIDATION: frozenset(
        {OptimizationStatus.SELECTING, OptimizationStatus.FAILED}
    ),
    OptimizationStatus.SELECTING: frozenset(
        {OptimizationStatus.RUNNING_HOLDOUT, OptimizationStatus.FAILED}
    ),
    OptimizationStatus.RUNNING_HOLDOUT: frozenset(
        {OptimizationStatus.COMPLETED, OptimizationStatus.FAILED}
    ),
    OptimizationStatus.COMPLETED: frozenset(),
    OptimizationStatus.FAILED: frozenset(),
    OptimizationStatus.CANCELLED: frozenset(),
}


def is_transition_allowed(current: OptimizationStatus, next_status: OptimizationStatus) -> bool:
    return next_status in _ALLOWED_TRANSITIONS[current]


class CandidateStatus(StrEnum):
    PENDING = "pending"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class ObjectiveStatus(StrEnum):
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"


class OptimizationValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_grid_inputs(fast_windows: list[int], slow_windows: list[int]) -> None:
    if not fast_windows or not slow_windows:
        raise OptimizationValidationError(
            "invalid_grid", "fast_windows and slow_windows must each declare at least one value"
        )
    for window in [*fast_windows, *slow_windows]:
        if window < 1:
            raise OptimizationValidationError(
                "invalid_grid", "grid window values must be positive integers"
            )


def canonicalize_grid(fast_windows: list[int], slow_windows: list[int]) -> list[tuple[int, int]]:
    """Deterministic, insertion-order-independent (fast_window, slow_window) enumeration."""
    fast_sorted = sorted(set(fast_windows))
    slow_sorted = sorted(set(slow_windows))
    return sorted({(fast, slow) for fast in fast_sorted for slow in slow_sorted})


def is_valid_candidate_pair(fast_window: int, slow_window: int) -> bool:
    return fast_window < slow_window


def validate_partitions(
    *,
    train_start: date,
    train_end: date,
    validation_start: date,
    validation_end: date,
    holdout_start: date,
    holdout_end: date,
) -> None:
    ordered = (
        train_start,
        train_end,
        validation_start,
        validation_end,
        holdout_start,
        holdout_end,
    )
    if not (
        train_start <= train_end < validation_start <= validation_end < holdout_start <= holdout_end
    ):
        raise OptimizationValidationError(
            "invalid_partitions",
            "partitions must satisfy train_end < validation_start <= validation_end < "
            f"holdout_start <= holdout_end (received {ordered})",
        )


def validate_objective_metric(metric_key: str) -> None:
    if metric_key not in ALLOWED_OBJECTIVE_METRICS:
        raise OptimizationValidationError(
            "unsupported_objective",
            f"objective_metric_key must be one of {sorted(ALLOWED_OBJECTIVE_METRICS)}",
        )


def validate_candidate_count(candidate_count: int, max_candidate_count: int) -> None:
    if candidate_count > max_candidate_count:
        raise OptimizationValidationError(
            "candidate_grid_too_large",
            f"grid expands to {candidate_count} candidates, exceeding the configured maximum of "
            f"{max_candidate_count}",
        )


def validate_partition_bar_coverage(
    *, partition_name: str, bar_count: int, largest_slow_window: int
) -> None:
    """Each partition needs the largest candidate's warm-up window, one eligible signal bar,
    and one further bar for that signal's next-bar-open fill opportunity."""
    minimum_required = largest_slow_window + 2
    if bar_count < minimum_required:
        raise OptimizationValidationError(
            "insufficient_partition_coverage",
            f"{partition_name} partition has {bar_count} eligible bars; needs at least "
            f"{minimum_required} for the largest candidate window ({largest_slow_window})",
        )


@dataclass(frozen=True, slots=True)
class CandidateSelectionInput:
    candidate_id: str
    fast_window: int
    slow_window: int
    objective_value: Decimal | None


def select_candidate(
    candidates: list[CandidateSelectionInput],
) -> CandidateSelectionInput | None:
    """Rank only candidates with an available objective value. An unavailable objective can
    never win. Tie-break: highest objective value, then lower slow_window, then lower
    fast_window, then canonical candidate ID."""
    eligible = [c for c in candidates if c.objective_value is not None]
    if not eligible:
        return None

    def sort_key(candidate: CandidateSelectionInput) -> tuple[Decimal, int, int, str]:
        value = candidate.objective_value
        assert value is not None
        return (-value, candidate.slow_window, candidate.fast_window, candidate.candidate_id)

    return min(eligible, key=sort_key)


@dataclass(frozen=True, slots=True)
class OptimizationCandidate:
    candidate_id: str
    optimization_id: str
    sequence: int
    fast_window: int
    slow_window: int
    status: CandidateStatus
    created_at_utc: datetime
    rejection_reason: str | None = None
    strategy_id: str | None = None
    strategy_version: int | None = None
    train_run_id: str | None = None
    validation_run_id: str | None = None
    objective_status: ObjectiveStatus | None = None
    objective_value: Decimal | None = None
    objective_reason: str | None = None
    warning_count: int = 0


@dataclass(frozen=True, slots=True)
class OptimizationManifest:
    optimization_id: str
    schema_version: int
    checksum: str
    dataset_id: str
    instrument_id: str
    base_strategy_name: str
    fast_window_grid: tuple[int, ...]
    slow_window_grid: tuple[int, ...]
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    holdout_start: date
    holdout_end: date
    capital_amount: Decimal
    capital_currency: str
    position_sizing_fraction: Decimal
    quantity_increment: Decimal
    money_scale: int
    annualization_basis: int
    risk_free_rate: Decimal
    objective_metric_key: str
    tie_break_rule: str
    max_candidate_count: int
    candidate_count: int
    rejected_count: int
    manifest_json: str
    status: OptimizationStatus
    created_at_utc: datetime
    failure_code: str | None = None
    selected_candidate_id: str | None = None
    selection_reason: str | None = None
    selection_audit_json: str | None = None
    selected_at_utc: datetime | None = None
    holdout_run_id: str | None = None
    holdout_objective_status: ObjectiveStatus | None = None
    holdout_objective_value: Decimal | None = None
    holdout_objective_reason: str | None = None
    started_at_utc: datetime | None = None
    finished_at_utc: datetime | None = None
