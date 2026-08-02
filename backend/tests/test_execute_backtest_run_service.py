from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.application.errors import (
    BacktestRunNotEligibleError,
    BacktestRunNotFoundError,
    EmptyBarSnapshotError,
    EngineExecutionError,
    UnresolvedInstrumentMappingError,
    UnsupportedMultiInstrumentError,
)
from app.application.execute_backtest_run_service import execute_backtest_run
from app.domain.backtest_manifest import (
    Capital,
    DatasetRef,
    EngineRef,
    Execution,
    Metrics,
    Period,
    PositionSizing,
    Rounding,
    RunManifestV1,
    StrategyRef,
    Universe,
)
from app.domain.backtest_run import BacktestRunStatus, RunManifest
from app.domain.execution_result import (
    ExecutionMetadata,
    ExecutionResult,
    TerminalStatus,
)
from app.domain.market_data import NormalizedBar
from app.domain.pagination import Page
from app.domain.strategy_spec import SignalPolicy, SmaCrossoverParameters, StrategySpecV1

BASE = datetime(2026, 1, 1, tzinfo=UTC)


class FakeRunRepository:
    def __init__(self, run: RunManifest) -> None:
        self.run = run
        self.transitions: list[dict[str, Any]] = []

    def create(self, run: RunManifest) -> RunManifest:
        raise NotImplementedError

    def get(self, run_id: str) -> RunManifest | None:
        return self.run if run_id == self.run.run_id else None

    def list(self, *, limit: int, offset: int) -> Page[RunManifest]:
        return Page(items=[self.run], total=1, limit=limit, offset=offset)

    def transition_status(
        self,
        run_id: str,
        *,
        expected_status: BacktestRunStatus,
        next_status: BacktestRunStatus,
        started_at_utc: datetime | None = None,
        finished_at_utc: datetime | None = None,
        failure_code: str | None = None,
    ) -> RunManifest:
        self.transitions.append({"next_status": next_status, "failure_code": failure_code})
        self.run = RunManifest(
            run_id=self.run.run_id,
            dataset_id=self.run.dataset_id,
            strategy_spec_version=self.run.strategy_spec_version,
            engine_version=self.run.engine_version,
            configuration_json=self.run.configuration_json,
            status=next_status,
            created_at_utc=self.run.created_at_utc,
            started_at_utc=started_at_utc or self.run.started_at_utc,
            finished_at_utc=finished_at_utc or self.run.finished_at_utc,
            failure_code=failure_code,
            schema_version=self.run.schema_version,
            manifest_checksum=self.run.manifest_checksum,
            strategy_id=self.run.strategy_id,
            strategy_version=self.run.strategy_version,
        )
        return self.run


class FakeStrategyRepository:
    def __init__(self, spec: StrategySpecV1) -> None:
        self._spec = spec

    def create(self, spec: StrategySpecV1) -> StrategySpecV1:
        return spec

    def get(self, strategy_id: str, version: int) -> StrategySpecV1 | None:
        return self._spec

    def list(self, *, limit: int, offset: int) -> Page[StrategySpecV1]:
        return Page(items=[], total=0, limit=limit, offset=offset)


class FakeBarSnapshotRepository:
    def __init__(
        self, bars: list[NormalizedBar] | None = None, error: Exception | None = None
    ) -> None:
        self._bars = bars or []
        self._error = error

    def get_snapshot(
        self, *, dataset_id: str, instrument_id: str, start_date: date, end_date: date
    ) -> list[NormalizedBar]:
        if self._error is not None:
            raise self._error
        return self._bars


class FakeEngine:
    def __init__(
        self, result: ExecutionResult | None = None, error: Exception | None = None
    ) -> None:
        self._result = result
        self._error = error
        self.called = False

    def execute(self, **kwargs: Any) -> ExecutionResult:
        self.called = True
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _strategy() -> StrategySpecV1:
    return StrategySpecV1(
        strategy_id="strat-1",
        version=1,
        schema_version=1,
        name="SMA 10/30",
        kind="sma_crossover",
        parameters=SmaCrossoverParameters(fast_window=10, slow_window=30, price_field="close"),
        signal_policy=SignalPolicy(signal_time="bar_close", eligible_after_bars=30, long_only=True),
        created_at_utc=BASE,
        checksum="sha256:aaa",
        canonical_json="{}",
    )


def _manifest() -> RunManifestV1:
    return RunManifestV1(
        run_id="run-1",
        strategy_ref=StrategyRef(strategy_id="strat-1", version=1, checksum="sha256:aaa"),
        dataset_ref=DatasetRef(dataset_id="ds-1", content_checksum="sha256:bbb"),
        universe=Universe(instrument_ids=("ins-1",)),
        period=Period(start_date=date(2020, 1, 1), end_date=date(2020, 12, 31), bar_interval="1d"),
        capital=Capital(amount=Decimal("100000000.00"), currency="IDR"),
        execution=Execution(
            position_sizing=PositionSizing(fraction=Decimal("1.00")),
            rounding=Rounding(quantity_increment=Decimal("1"), money_scale=2),
        ),
        metrics=Metrics(annualization_basis=252, risk_free_rate=Decimal("0.00")),
        engine_ref=EngineRef(adapter_name="backtrader", adapter_version="unimplemented"),
        created_at_utc=BASE,
    )


def _multi_instrument_manifest() -> RunManifestV1:
    manifest = _manifest()
    return RunManifestV1(
        run_id=manifest.run_id,
        strategy_ref=manifest.strategy_ref,
        dataset_ref=manifest.dataset_ref,
        universe=Universe(instrument_ids=("ins-1", "ins-2")),
        period=manifest.period,
        capital=manifest.capital,
        execution=manifest.execution,
        metrics=manifest.metrics,
        engine_ref=manifest.engine_ref,
        created_at_utc=manifest.created_at_utc,
    )


def _run(
    manifest: RunManifestV1, status: BacktestRunStatus = BacktestRunStatus.CREATED
) -> RunManifest:
    import json

    return RunManifest(
        run_id=manifest.run_id,
        dataset_id=manifest.dataset_ref.dataset_id,
        strategy_spec_version="strat-1@1",
        engine_version="unimplemented",
        configuration_json=json.dumps(manifest.to_canonical_dict()),
        status=status,
        created_at_utc=BASE,
        schema_version=1,
        manifest_checksum="sha256:manifest",
        strategy_id="strat-1",
        strategy_version=1,
    )


def _bar(idx: int) -> NormalizedBar:
    from datetime import timedelta

    close = Decimal(100 + idx)
    return NormalizedBar(
        bar_id=f"bar-{idx}",
        dataset_id="ds-1",
        source_instrument_identifier="BBCA",
        timestamp_utc=BASE + timedelta(days=idx),
        bar_interval="1d",
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=1000,
    )


def _completed_result() -> ExecutionResult:
    return ExecutionResult(
        metadata=ExecutionMetadata(
            adapter_name="backtrader",
            adapter_version="1.0",
            manifest_checksum="sha256:manifest",
            dataset_checksum="sha256:bbb",
            ordering_policy="stable_by_instrument_id",
            started_at_utc=BASE,
            finished_at_utc=BASE,
            event_count=0,
        ),
        order_events=(),
        fill_events=(),
        position_events=(),
        cash_events=(),
        warnings=(),
        terminal_status=TerminalStatus.COMPLETED,
    )


def test_raises_when_run_not_found() -> None:
    run_repository = FakeRunRepository(_run(_manifest()))
    with pytest.raises(BacktestRunNotFoundError):
        execute_backtest_run(
            run_repository,
            FakeStrategyRepository(_strategy()),
            FakeBarSnapshotRepository([_bar(0)]),
            FakeEngine(_completed_result()),
            "does-not-exist",
            id_factory=lambda: "id",
        )


def test_raises_when_run_not_eligible() -> None:
    run_repository = FakeRunRepository(_run(_manifest(), status=BacktestRunStatus.COMPLETED))
    with pytest.raises(BacktestRunNotEligibleError):
        execute_backtest_run(
            run_repository,
            FakeStrategyRepository(_strategy()),
            FakeBarSnapshotRepository([_bar(0)]),
            FakeEngine(_completed_result()),
            "run-1",
            id_factory=lambda: "id",
        )


def test_raises_and_fails_run_on_multi_instrument_manifest() -> None:
    run_repository = FakeRunRepository(_run(_multi_instrument_manifest()))
    with pytest.raises(UnsupportedMultiInstrumentError):
        execute_backtest_run(
            run_repository,
            FakeStrategyRepository(_strategy()),
            FakeBarSnapshotRepository([_bar(0)]),
            FakeEngine(_completed_result()),
            "run-1",
            id_factory=lambda: "id",
        )
    assert run_repository.run.status == BacktestRunStatus.FAILED
    assert run_repository.run.failure_code == "unsupported_multi_instrument"


def test_raises_and_fails_run_on_unresolved_mapping() -> None:
    run_repository = FakeRunRepository(_run(_manifest()))
    error = UnresolvedInstrumentMappingError("ds-1", "ins-1")
    with pytest.raises(UnresolvedInstrumentMappingError):
        execute_backtest_run(
            run_repository,
            FakeStrategyRepository(_strategy()),
            FakeBarSnapshotRepository(error=error),
            FakeEngine(_completed_result()),
            "run-1",
            id_factory=lambda: "id",
        )
    assert run_repository.run.status == BacktestRunStatus.FAILED
    assert run_repository.run.failure_code == "unresolved_instrument_mapping"


def test_raises_and_fails_run_on_empty_bar_snapshot() -> None:
    run_repository = FakeRunRepository(_run(_manifest()))
    with pytest.raises(EmptyBarSnapshotError):
        execute_backtest_run(
            run_repository,
            FakeStrategyRepository(_strategy()),
            FakeBarSnapshotRepository([]),
            FakeEngine(_completed_result()),
            "run-1",
            id_factory=lambda: "id",
        )
    assert run_repository.run.status == BacktestRunStatus.FAILED
    assert run_repository.run.failure_code == "empty_bar_snapshot"


def test_transitions_through_running_to_completed_on_success() -> None:
    run_repository = FakeRunRepository(_run(_manifest()))
    engine = FakeEngine(_completed_result())

    result = execute_backtest_run(
        run_repository,
        FakeStrategyRepository(_strategy()),
        FakeBarSnapshotRepository([_bar(0)]),
        engine,
        "run-1",
        id_factory=lambda: "id",
    )

    assert engine.called
    assert result.terminal_status == TerminalStatus.COMPLETED
    assert [t["next_status"] for t in run_repository.transitions] == [
        BacktestRunStatus.RUNNING,
        BacktestRunStatus.COMPLETED,
    ]
    assert run_repository.run.status == BacktestRunStatus.COMPLETED


def test_transitions_to_failed_when_engine_reports_failure() -> None:
    failed_result = ExecutionResult(
        metadata=_completed_result().metadata,
        order_events=(),
        fill_events=(),
        position_events=(),
        cash_events=(),
        warnings=(),
        terminal_status=TerminalStatus.FAILED,
        failure_code="missing_next_bar",
    )
    run_repository = FakeRunRepository(_run(_manifest()))

    result = execute_backtest_run(
        run_repository,
        FakeStrategyRepository(_strategy()),
        FakeBarSnapshotRepository([_bar(0)]),
        FakeEngine(failed_result),
        "run-1",
        id_factory=lambda: "id",
    )

    assert result.failure_code == "missing_next_bar"
    assert run_repository.run.status == BacktestRunStatus.FAILED
    assert run_repository.run.failure_code == "missing_next_bar"


def test_raises_engine_execution_error_when_engine_crashes_unexpectedly() -> None:
    run_repository = FakeRunRepository(_run(_manifest()))
    engine = FakeEngine(error=RuntimeError("boom"))

    with pytest.raises(EngineExecutionError):
        execute_backtest_run(
            run_repository,
            FakeStrategyRepository(_strategy()),
            FakeBarSnapshotRepository([_bar(0)]),
            engine,
            "run-1",
            id_factory=lambda: "id",
        )

    assert run_repository.run.status == BacktestRunStatus.FAILED
    assert run_repository.run.failure_code == "engine_error"
