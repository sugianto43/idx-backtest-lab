import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.application.backtest_run_manifest_service import (
    CreateRunManifestRequest,
    create_run_manifest,
)
from app.application.errors import (
    ApplicationError,
    OptimizationNotEligibleError,
    OptimizationNotFoundError,
)
from app.application.execute_backtest_run_service import execute_backtest_run
from app.application.ports.backtest_run_repository import BacktestRunRepository
from app.application.ports.bar_snapshot_repository import BarSnapshotRepository
from app.application.ports.dataset_repository import DatasetRepository
from app.application.ports.engine_execution_port import EngineExecutionPort
from app.application.ports.instrument_repository import InstrumentRepository
from app.application.ports.optimization_repository import OptimizationRepository
from app.application.ports.run_artifact_repository import RunArtifactRepository
from app.application.ports.run_artifact_writer import RunArtifactWriter
from app.application.ports.strategy_spec_repository import StrategySpecRepository
from app.application.strategy_spec_service import create_strategy_spec
from app.domain.execution_result import TerminalStatus
from app.domain.optimization import (
    CandidateSelectionInput,
    CandidateStatus,
    ObjectiveStatus,
    OptimizationCandidate,
    OptimizationManifest,
    OptimizationStatus,
    select_candidate,
)

_PRICE_FIELD = "close"
_SIGNAL_TIME = "bar_close"


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def _default_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class OptimizationExecutionPorts:
    optimization_repository: OptimizationRepository
    strategy_repository: StrategySpecRepository
    dataset_repository: DatasetRepository
    instrument_repository: InstrumentRepository
    run_repository: BacktestRunRepository
    bar_snapshot_repository: BarSnapshotRepository
    run_artifact_repository: RunArtifactRepository
    engine: EngineExecutionPort
    artifact_writer: RunArtifactWriter


def _run_period(
    ports: OptimizationExecutionPorts,
    manifest: OptimizationManifest,
    *,
    strategy_id: str,
    strategy_version: int,
    start_date: date,
    end_date: date,
    id_factory: Callable[[], str],
    clock: Callable[[], datetime],
) -> tuple[str, TerminalStatus]:
    run = create_run_manifest(
        ports.run_repository,
        ports.strategy_repository,
        ports.dataset_repository,
        ports.instrument_repository,
        CreateRunManifestRequest(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            dataset_id=manifest.dataset_id,
            instrument_ids=(manifest.instrument_id,),
            start_date=start_date,
            end_date=end_date,
            capital_amount=str(manifest.capital_amount),
            capital_currency=manifest.capital_currency,
            position_sizing_fraction=str(manifest.position_sizing_fraction),
            quantity_increment=str(manifest.quantity_increment),
            money_scale=manifest.money_scale,
            annualization_basis=manifest.annualization_basis,
            risk_free_rate=str(manifest.risk_free_rate),
        ),
        id_factory=id_factory,
        clock=clock,
    )
    result = execute_backtest_run(
        ports.run_repository,
        ports.strategy_repository,
        ports.bar_snapshot_repository,
        ports.engine,
        run.run_id,
        id_factory=id_factory,
        clock=clock,
        artifact_writer=ports.artifact_writer,
    )
    return run.run_id, result.terminal_status


def _objective_from_run(
    run_artifact_repository: RunArtifactRepository, run_id: str, objective_metric_key: str
) -> tuple[ObjectiveStatus, str | None, str | None]:
    metrics = run_artifact_repository.list_metrics(run_id)
    match = next((metric for metric in metrics if metric.metric_key == objective_metric_key), None)
    if match is None or match.value is None:
        reason = match.reason if match is not None else "objective_metric_not_computed"
        return ObjectiveStatus.NOT_AVAILABLE, None, reason
    return ObjectiveStatus.AVAILABLE, str(match.value), None


def _warning_total(run_artifact_repository: RunArtifactRepository, run_id: str) -> int:
    return run_artifact_repository.list_warnings(run_id, limit=1, offset=0).total


def _try_fail(
    optimization_repository: OptimizationRepository,
    optimization_id: str,
    current_status: OptimizationStatus,
    failure_code: str,
    clock: Callable[[], datetime],
) -> None:
    try:
        optimization_repository.transition_status(
            optimization_id,
            expected_status=current_status,
            next_status=OptimizationStatus.FAILED,
            finished_at_utc=clock(),
            failure_code=failure_code,
        )
    except ApplicationError:
        pass


def _execute_candidate(
    ports: OptimizationExecutionPorts,
    manifest: OptimizationManifest,
    candidate: OptimizationCandidate,
    *,
    id_factory: Callable[[], str],
    clock: Callable[[], datetime],
) -> None:
    strategy_name = (
        f"{manifest.base_strategy_name} (fast={candidate.fast_window}, "
        f"slow={candidate.slow_window})"
    )
    spec = create_strategy_spec(
        ports.strategy_repository,
        name=strategy_name,
        kind="sma_crossover",
        fast_window=candidate.fast_window,
        slow_window=candidate.slow_window,
        price_field=_PRICE_FIELD,
        signal_time=_SIGNAL_TIME,
        eligible_after_bars=candidate.slow_window,
        long_only=True,
        id_factory=id_factory,
        clock=clock,
    )

    train_run_id, train_terminal = _run_period(
        ports,
        manifest,
        strategy_id=spec.strategy_id,
        strategy_version=spec.version,
        start_date=manifest.train_start,
        end_date=manifest.train_end,
        id_factory=id_factory,
        clock=clock,
    )

    if train_terminal == TerminalStatus.FAILED:
        ports.optimization_repository.record_candidate_result(
            candidate.candidate_id,
            status=CandidateStatus.FAILED.value,
            strategy_id=spec.strategy_id,
            strategy_version=spec.version,
            train_run_id=train_run_id,
            validation_run_id=None,
            objective_status=ObjectiveStatus.NOT_AVAILABLE,
            objective_value=None,
            objective_reason="train_run_failed",
            warning_count=_warning_total(ports.run_artifact_repository, train_run_id),
        )
        return

    validation_run_id, validation_terminal = _run_period(
        ports,
        manifest,
        strategy_id=spec.strategy_id,
        strategy_version=spec.version,
        start_date=manifest.validation_start,
        end_date=manifest.validation_end,
        id_factory=id_factory,
        clock=clock,
    )

    warning_count = _warning_total(ports.run_artifact_repository, train_run_id) + _warning_total(
        ports.run_artifact_repository, validation_run_id
    )

    if validation_terminal == TerminalStatus.FAILED:
        ports.optimization_repository.record_candidate_result(
            candidate.candidate_id,
            status=CandidateStatus.FAILED.value,
            strategy_id=spec.strategy_id,
            strategy_version=spec.version,
            train_run_id=train_run_id,
            validation_run_id=validation_run_id,
            objective_status=ObjectiveStatus.NOT_AVAILABLE,
            objective_value=None,
            objective_reason="validation_run_failed",
            warning_count=warning_count,
        )
        return

    objective_status, objective_value, objective_reason = _objective_from_run(
        ports.run_artifact_repository, validation_run_id, manifest.objective_metric_key
    )
    ports.optimization_repository.record_candidate_result(
        candidate.candidate_id,
        status=CandidateStatus.COMPLETED.value,
        strategy_id=spec.strategy_id,
        strategy_version=spec.version,
        train_run_id=train_run_id,
        validation_run_id=validation_run_id,
        objective_status=objective_status,
        objective_value=objective_value,
        objective_reason=objective_reason,
        warning_count=warning_count,
    )


def _run_train_validation_phase(
    ports: OptimizationExecutionPorts,
    optimization_id: str,
    manifest: OptimizationManifest,
    total_candidates: int,
    *,
    id_factory: Callable[[], str],
    clock: Callable[[], datetime],
) -> None:
    candidates = ports.optimization_repository.list_candidates(
        optimization_id, limit=total_candidates, offset=0
    ).items
    try:
        for candidate in candidates:
            if candidate.status != CandidateStatus.PENDING:
                continue
            _execute_candidate(ports, manifest, candidate, id_factory=id_factory, clock=clock)
    except Exception:
        _try_fail(
            ports.optimization_repository,
            optimization_id,
            OptimizationStatus.RUNNING_TRAIN_VALIDATION,
            "unexpected_error",
            clock,
        )
        raise


def _select_candidate(
    ports: OptimizationExecutionPorts,
    optimization_id: str,
    manifest: OptimizationManifest,
    total_candidates: int,
    *,
    clock: Callable[[], datetime],
) -> tuple[list[OptimizationCandidate], CandidateSelectionInput | None]:
    completed_candidates = ports.optimization_repository.list_candidates(
        optimization_id, limit=total_candidates, offset=0
    ).items
    selection_inputs = [
        CandidateSelectionInput(
            candidate_id=candidate.candidate_id,
            fast_window=candidate.fast_window,
            slow_window=candidate.slow_window,
            objective_value=(
                Decimal(candidate.objective_value)
                if candidate.objective_status == ObjectiveStatus.AVAILABLE
                and candidate.objective_value is not None
                else None
            ),
        )
        for candidate in completed_candidates
        if candidate.status == CandidateStatus.COMPLETED
    ]
    selected = select_candidate(selection_inputs)

    audit = [
        {
            "candidate_id": candidate.candidate_id,
            "sequence": candidate.sequence,
            "fast_window": candidate.fast_window,
            "slow_window": candidate.slow_window,
            "status": candidate.status.value,
            "objective_status": (
                candidate.objective_status.value if candidate.objective_status else None
            ),
            "objective_value": (
                str(candidate.objective_value) if candidate.objective_value is not None else None
            ),
        }
        for candidate in completed_candidates
    ]
    audit_json = json.dumps(audit, sort_keys=True, separators=(",", ":"))

    if selected is None:
        ports.optimization_repository.record_selection(
            optimization_id,
            selected_candidate_id=None,
            selection_reason="no_eligible_candidate",
            selection_audit_json=audit_json,
            selected_at_utc=clock(),
        )
    else:
        ports.optimization_repository.record_selection(
            optimization_id,
            selected_candidate_id=selected.candidate_id,
            selection_reason=f"highest {manifest.objective_metric_key}",
            selection_audit_json=audit_json,
            selected_at_utc=clock(),
        )
    return completed_candidates, selected


def execute_optimization(
    ports: OptimizationExecutionPorts,
    optimization_id: str,
    *,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime] = _default_clock,
) -> OptimizationManifest:
    optimization_repository = ports.optimization_repository
    manifest = optimization_repository.get(optimization_id)
    if manifest is None:
        raise OptimizationNotFoundError(optimization_id)
    if manifest.status != OptimizationStatus.CREATED:
        raise OptimizationNotEligibleError(optimization_id, manifest.status.value)

    optimization_repository.transition_status(
        optimization_id,
        expected_status=OptimizationStatus.CREATED,
        next_status=OptimizationStatus.VALIDATING,
        started_at_utc=clock(),
    )
    optimization_repository.transition_status(
        optimization_id,
        expected_status=OptimizationStatus.VALIDATING,
        next_status=OptimizationStatus.RUNNING_TRAIN_VALIDATION,
    )

    total_candidates = manifest.candidate_count + manifest.rejected_count
    _run_train_validation_phase(
        ports, optimization_id, manifest, total_candidates, id_factory=id_factory, clock=clock
    )

    optimization_repository.transition_status(
        optimization_id,
        expected_status=OptimizationStatus.RUNNING_TRAIN_VALIDATION,
        next_status=OptimizationStatus.SELECTING,
    )

    completed_candidates, selected = _select_candidate(
        ports, optimization_id, manifest, total_candidates, clock=clock
    )

    if selected is None:
        optimization_repository.transition_status(
            optimization_id,
            expected_status=OptimizationStatus.SELECTING,
            next_status=OptimizationStatus.FAILED,
            finished_at_utc=clock(),
            failure_code="no_eligible_candidate",
        )
        result = optimization_repository.get(optimization_id)
        assert result is not None
        return result

    optimization_repository.transition_status(
        optimization_id,
        expected_status=OptimizationStatus.SELECTING,
        next_status=OptimizationStatus.RUNNING_HOLDOUT,
    )

    selected_candidate = next(
        candidate
        for candidate in completed_candidates
        if candidate.candidate_id == selected.candidate_id
    )
    assert selected_candidate.strategy_id is not None
    assert selected_candidate.strategy_version is not None

    try:
        holdout_run_id, holdout_terminal_status = _run_period(
            ports,
            manifest,
            strategy_id=selected_candidate.strategy_id,
            strategy_version=selected_candidate.strategy_version,
            start_date=manifest.holdout_start,
            end_date=manifest.holdout_end,
            id_factory=id_factory,
            clock=clock,
        )
    except Exception:
        _try_fail(
            optimization_repository,
            optimization_id,
            OptimizationStatus.RUNNING_HOLDOUT,
            "unexpected_error",
            clock,
        )
        raise

    holdout_status: ObjectiveStatus
    holdout_value: str | None
    holdout_reason: str | None
    if holdout_terminal_status == TerminalStatus.FAILED:
        holdout_status, holdout_value, holdout_reason = (
            ObjectiveStatus.NOT_AVAILABLE,
            None,
            "holdout_run_failed",
        )
    else:
        holdout_status, holdout_value, holdout_reason = _objective_from_run(
            ports.run_artifact_repository, holdout_run_id, manifest.objective_metric_key
        )

    optimization_repository.record_holdout_result(
        optimization_id,
        holdout_run_id=holdout_run_id,
        holdout_objective_status=holdout_status,
        holdout_objective_value=holdout_value,
        holdout_objective_reason=holdout_reason,
    )
    optimization_repository.transition_status(
        optimization_id,
        expected_status=OptimizationStatus.RUNNING_HOLDOUT,
        next_status=OptimizationStatus.COMPLETED,
        finished_at_utc=clock(),
    )

    result = optimization_repository.get(optimization_id)
    assert result is not None
    return result
