import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from app.application.errors import DatasetNotFoundError, InstrumentNotFoundError
from app.application.ports.bar_snapshot_repository import BarSnapshotRepository
from app.application.ports.dataset_repository import DatasetRepository
from app.application.ports.instrument_repository import InstrumentRepository
from app.application.ports.optimization_repository import OptimizationRepository
from app.domain.checksum import canonical_json_bytes, compute_checksum
from app.domain.optimization import (
    OPTIMIZATION_SCHEMA_VERSION,
    TIE_BREAK_RULE,
    CandidateStatus,
    OptimizationCandidate,
    OptimizationManifest,
    OptimizationStatus,
    canonicalize_grid,
    is_valid_candidate_pair,
    validate_candidate_count,
    validate_grid_inputs,
    validate_objective_metric,
    validate_partition_bar_coverage,
    validate_partitions,
)


class OptimizationDecimalFieldError(ValueError):
    def __init__(self, field: str) -> None:
        super().__init__(f"{field} must be a valid decimal string")
        self.field = field


def _parse_decimal(value: str, field: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise OptimizationDecimalFieldError(field) from exc


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def _default_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CreateOptimizationRequest:
    dataset_id: str
    instrument_id: str
    base_strategy_name: str
    fast_windows: list[int]
    slow_windows: list[int]
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    holdout_start: date
    holdout_end: date
    capital_amount: str
    capital_currency: str
    position_sizing_fraction: str
    quantity_increment: str
    money_scale: int
    annualization_basis: int
    risk_free_rate: str
    objective_metric_key: str


def create_optimization(
    optimization_repository: OptimizationRepository,
    dataset_repository: DatasetRepository,
    instrument_repository: InstrumentRepository,
    bar_snapshot_repository: BarSnapshotRepository,
    request: CreateOptimizationRequest,
    *,
    max_candidate_count: int,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime] = _default_clock,
) -> OptimizationManifest:
    validate_grid_inputs(request.fast_windows, request.slow_windows)
    validate_partitions(
        train_start=request.train_start,
        train_end=request.train_end,
        validation_start=request.validation_start,
        validation_end=request.validation_end,
        holdout_start=request.holdout_start,
        holdout_end=request.holdout_end,
    )
    validate_objective_metric(request.objective_metric_key)

    dataset = dataset_repository.get(request.dataset_id)
    if dataset is None:
        raise DatasetNotFoundError(request.dataset_id)
    if instrument_repository.get(request.instrument_id) is None:
        raise InstrumentNotFoundError(request.instrument_id)

    canonical_pairs = canonicalize_grid(request.fast_windows, request.slow_windows)
    validate_candidate_count(len(canonical_pairs), max_candidate_count)

    valid_pairs = [pair for pair in canonical_pairs if is_valid_candidate_pair(*pair)]
    largest_slow_window = max((slow for _, slow in valid_pairs), default=max(request.slow_windows))

    for partition_name, start, end in (
        ("train", request.train_start, request.train_end),
        ("validation", request.validation_start, request.validation_end),
        ("holdout", request.holdout_start, request.holdout_end),
    ):
        bars = bar_snapshot_repository.get_snapshot(
            dataset_id=request.dataset_id,
            instrument_id=request.instrument_id,
            start_date=start,
            end_date=end,
        )
        validate_partition_bar_coverage(
            partition_name=partition_name,
            bar_count=len(bars),
            largest_slow_window=largest_slow_window,
        )

    capital_amount = _parse_decimal(request.capital_amount, "capital_amount")
    position_sizing_fraction = _parse_decimal(
        request.position_sizing_fraction, "position_sizing_fraction"
    )
    quantity_increment = _parse_decimal(request.quantity_increment, "quantity_increment")
    risk_free_rate = _parse_decimal(request.risk_free_rate, "risk_free_rate")

    optimization_id = id_factory()
    created_at = clock()

    canonical = {
        "schema_version": OPTIMIZATION_SCHEMA_VERSION,
        "optimization_id": optimization_id,
        "dataset_id": dataset.dataset_id,
        "dataset_content_checksum": dataset.content_checksum,
        "instrument_id": request.instrument_id,
        "base_strategy_name": request.base_strategy_name,
        "fast_window_grid": sorted(set(request.fast_windows)),
        "slow_window_grid": sorted(set(request.slow_windows)),
        "candidate_pairs": [list(pair) for pair in canonical_pairs],
        "train": {"start": request.train_start.isoformat(), "end": request.train_end.isoformat()},
        "validation": {
            "start": request.validation_start.isoformat(),
            "end": request.validation_end.isoformat(),
        },
        "holdout": {
            "start": request.holdout_start.isoformat(),
            "end": request.holdout_end.isoformat(),
        },
        "capital": {"amount": str(capital_amount), "currency": request.capital_currency},
        "execution": {
            "position_sizing_fraction": str(position_sizing_fraction),
            "quantity_increment": str(quantity_increment),
            "money_scale": request.money_scale,
        },
        "metrics": {
            "annualization_basis": request.annualization_basis,
            "risk_free_rate": str(risk_free_rate),
        },
        "objective_metric_key": request.objective_metric_key,
        "tie_break_rule": TIE_BREAK_RULE,
        "max_candidate_count": max_candidate_count,
        "created_at_utc": created_at.isoformat().replace("+00:00", "Z"),
    }
    checksum = compute_checksum(canonical)
    manifest_json = canonical_json_bytes(canonical).decode("utf-8")

    candidates = [
        OptimizationCandidate(
            candidate_id=id_factory(),
            optimization_id=optimization_id,
            sequence=sequence,
            fast_window=fast_window,
            slow_window=slow_window,
            status=(
                CandidateStatus.PENDING
                if is_valid_candidate_pair(fast_window, slow_window)
                else CandidateStatus.REJECTED
            ),
            rejection_reason=(
                None
                if is_valid_candidate_pair(fast_window, slow_window)
                else "fast_window must be less than slow_window"
            ),
            created_at_utc=created_at,
        )
        for sequence, (fast_window, slow_window) in enumerate(canonical_pairs)
    ]

    manifest = OptimizationManifest(
        optimization_id=optimization_id,
        schema_version=OPTIMIZATION_SCHEMA_VERSION,
        checksum=checksum,
        dataset_id=dataset.dataset_id,
        instrument_id=request.instrument_id,
        base_strategy_name=request.base_strategy_name,
        fast_window_grid=tuple(sorted(set(request.fast_windows))),
        slow_window_grid=tuple(sorted(set(request.slow_windows))),
        train_start=request.train_start,
        train_end=request.train_end,
        validation_start=request.validation_start,
        validation_end=request.validation_end,
        holdout_start=request.holdout_start,
        holdout_end=request.holdout_end,
        capital_amount=capital_amount,
        capital_currency=request.capital_currency,
        position_sizing_fraction=position_sizing_fraction,
        quantity_increment=quantity_increment,
        money_scale=request.money_scale,
        annualization_basis=request.annualization_basis,
        risk_free_rate=risk_free_rate,
        objective_metric_key=request.objective_metric_key,
        tie_break_rule=TIE_BREAK_RULE,
        max_candidate_count=max_candidate_count,
        candidate_count=len(valid_pairs),
        rejected_count=len(canonical_pairs) - len(valid_pairs),
        manifest_json=manifest_json,
        status=OptimizationStatus.CREATED,
        created_at_utc=created_at,
    )

    optimization_repository.create(manifest, candidates)
    return manifest
