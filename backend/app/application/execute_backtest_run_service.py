import json
from collections.abc import Callable
from datetime import UTC, datetime

from app.application.errors import (
    BacktestRunNotEligibleError,
    BacktestRunNotFoundError,
    EmptyBarSnapshotError,
    EngineExecutionError,
    StrategySpecNotFoundError,
    UnsupportedMultiInstrumentError,
)
from app.application.ports.backtest_run_repository import BacktestRunRepository
from app.application.ports.bar_snapshot_repository import BarSnapshotRepository
from app.application.ports.engine_execution_port import EngineExecutionPort
from app.application.ports.strategy_spec_repository import StrategySpecRepository
from app.domain.backtest_manifest import parse_run_manifest
from app.domain.backtest_run import BacktestRunStatus
from app.domain.execution_result import ExecutionResult, TerminalStatus


def _default_clock() -> datetime:
    return datetime.now(UTC)


def execute_backtest_run(
    run_repository: BacktestRunRepository,
    strategy_repository: StrategySpecRepository,
    bar_snapshot_repository: BarSnapshotRepository,
    engine: EngineExecutionPort,
    run_id: str,
    *,
    id_factory: Callable[[], str],
    clock: Callable[[], datetime] = _default_clock,
) -> ExecutionResult:
    run = run_repository.get(run_id)
    if run is None:
        raise BacktestRunNotFoundError(run_id)
    if run.status != BacktestRunStatus.CREATED:
        raise BacktestRunNotEligibleError(run_id, run.status.value)

    manifest = parse_run_manifest(json.loads(run.configuration_json))

    strategy = strategy_repository.get(
        manifest.strategy_ref.strategy_id, manifest.strategy_ref.version
    )
    if strategy is None or strategy.checksum != manifest.strategy_ref.checksum:
        raise StrategySpecNotFoundError(
            manifest.strategy_ref.strategy_id, manifest.strategy_ref.version
        )

    if len(manifest.universe.instrument_ids) != 1:
        run_repository.transition_status(
            run_id,
            expected_status=BacktestRunStatus.CREATED,
            next_status=BacktestRunStatus.FAILED,
            finished_at_utc=clock(),
            failure_code="unsupported_multi_instrument",
        )
        raise UnsupportedMultiInstrumentError(run_id)

    instrument_id = manifest.universe.instrument_ids[0]

    try:
        bars = bar_snapshot_repository.get_snapshot(
            dataset_id=manifest.dataset_ref.dataset_id,
            instrument_id=instrument_id,
            start_date=manifest.period.start_date,
            end_date=manifest.period.end_date,
        )
    except Exception as exc:
        run_repository.transition_status(
            run_id,
            expected_status=BacktestRunStatus.CREATED,
            next_status=BacktestRunStatus.FAILED,
            finished_at_utc=clock(),
            failure_code="unresolved_instrument_mapping",
        )
        raise exc

    if not bars:
        run_repository.transition_status(
            run_id,
            expected_status=BacktestRunStatus.CREATED,
            next_status=BacktestRunStatus.FAILED,
            finished_at_utc=clock(),
            failure_code="empty_bar_snapshot",
        )
        raise EmptyBarSnapshotError(run_id)

    run_repository.transition_status(
        run_id,
        expected_status=BacktestRunStatus.CREATED,
        next_status=BacktestRunStatus.RUNNING,
        started_at_utc=clock(),
    )

    try:
        result = engine.execute(
            manifest=manifest,
            manifest_checksum=run.manifest_checksum or "",
            strategy=strategy,
            instrument_id=instrument_id,
            bars=bars,
            id_factory=id_factory,
            clock=clock,
        )
    except Exception as exc:
        run_repository.transition_status(
            run_id,
            expected_status=BacktestRunStatus.RUNNING,
            next_status=BacktestRunStatus.FAILED,
            finished_at_utc=clock(),
            failure_code="engine_error",
        )
        raise EngineExecutionError("engine_error", str(exc)) from exc

    if result.terminal_status == TerminalStatus.FAILED:
        run_repository.transition_status(
            run_id,
            expected_status=BacktestRunStatus.RUNNING,
            next_status=BacktestRunStatus.FAILED,
            finished_at_utc=clock(),
            failure_code=result.failure_code,
        )
    else:
        run_repository.transition_status(
            run_id,
            expected_status=BacktestRunStatus.RUNNING,
            next_status=BacktestRunStatus.COMPLETED,
            finished_at_utc=clock(),
        )

    return result
