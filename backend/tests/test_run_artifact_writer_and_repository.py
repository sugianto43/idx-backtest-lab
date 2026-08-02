from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import duckdb
import pytest

from app.domain.backtest_run import BacktestRunStatus, RunManifest
from app.domain.dataset import DatasetManifest, DatasetValidationStatus
from app.domain.execution_result import (
    CashEvent,
    ExecutionWarning,
    FillEvent,
    OrderEvent,
    OrderSide,
    OrderStatus,
    PositionEvent,
)
from app.domain.run_artifact import (
    MetricRecord,
    MetricStatus,
    PortfolioSnapshot,
    ReproducibilityManifest,
    RunArtifactBundle,
    SnapshotValuationStatus,
)
from app.infrastructure.db.backtest_run_repository import DuckDBBacktestRunRepository
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.migration_runner import run_migrations
from app.infrastructure.db.run_artifact_repository import DuckDBRunArtifactRepository
from app.infrastructure.db.run_artifact_writer import DuckDBRunArtifactWriter
from app.infrastructure.settings import Settings

DAY1 = datetime(2026, 1, 1, tzinfo=UTC)
DAY2 = datetime(2026, 1, 2, tzinfo=UTC)


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    db_path = tmp_path / "test.duckdb"
    connection = duckdb.connect(str(db_path))
    run_migrations(connection)
    connection.close()
    return Settings(database_path=str(db_path))


@pytest.fixture
def run_id(settings: Settings) -> str:
    dataset = DatasetManifest(
        dataset_id="ds-1",
        version=1,
        name="Sample dataset",
        source_name="synthetic-test",
        bar_interval="1d",
        timezone="UTC",
        adjustment_policy="unknown",
        validation_status=DatasetValidationStatus.VALID,
        created_at_utc=DAY1,
    )
    DuckDBDatasetRepository(settings).create(dataset)

    run = RunManifest(
        run_id="run-1",
        dataset_id="ds-1",
        strategy_spec_version="sma_crossover@1",
        engine_version="backtrader-adapter@0",
        configuration_json="{}",
        status=BacktestRunStatus.CREATED,
        created_at_utc=DAY1,
    )
    DuckDBBacktestRunRepository(settings).create(run)
    return run.run_id


def _bundle(run_id: str, *, terminal_status: str = "completed") -> RunArtifactBundle:
    return RunArtifactBundle(
        bundle_id="bundle-1",
        run_id=run_id,
        artifact_schema_version=1,
        checksum="checksum-1",
        terminal_status=terminal_status,
        provenance_json='{"run_id": "run-1"}',
        event_count=1,
        snapshot_count=1,
        metric_count=1,
        created_at_utc=DAY1,
    )


def test_persist_and_read_back_completed_run_artifact(settings: Settings, run_id: str) -> None:
    bundle = _bundle(run_id)
    order_events = [
        OrderEvent(
            order_id="order-1",
            instrument_id="BBCA",
            side=OrderSide.BUY,
            created_at_utc=DAY1,
            intended_quantity=5,
            status=OrderStatus.FILLED,
        )
    ]
    fill_events = [
        FillEvent(
            order_id="order-1",
            instrument_id="BBCA",
            side=OrderSide.BUY,
            filled_at_utc=DAY1,
            quantity=5,
            price=Decimal("100"),
            currency="IDR",
            commission=Decimal("0"),
            tax=Decimal("0"),
            slippage=Decimal("0"),
        )
    ]
    position_events = [
        PositionEvent(
            timestamp_utc=DAY1,
            instrument_id="BBCA",
            quantity=5,
            average_cost=Decimal("100"),
            reason="buy_fill",
        )
    ]
    cash_events = [
        CashEvent(
            timestamp_utc=DAY1,
            currency="IDR",
            cash_before=Decimal("1000"),
            cash_after=Decimal("500"),
            reason="buy_fill",
        )
    ]
    warnings = [
        ExecutionWarning(
            code="warn-1", message="something noted", instrument_id="BBCA", timestamp_utc=DAY1
        )
    ]
    snapshots = [
        PortfolioSnapshot(
            sequence=0,
            timestamp_utc=DAY1,
            cash=Decimal("500"),
            holdings_value=Decimal("500"),
            total_equity=Decimal("1000"),
            currency="IDR",
            status=SnapshotValuationStatus.VALID,
        )
    ]
    metrics = [
        MetricRecord(
            metric_key="initial_equity",
            status=MetricStatus.AVAILABLE,
            definition_version=1,
            calculation_input_json='{"capital_amount": "1000"}',
            value=Decimal("1000"),
        )
    ]
    manifest = ReproducibilityManifest(
        manifest_id="manifest-1",
        bundle_id=bundle.bundle_id,
        run_id=run_id,
        canonical_json='{"schema_version": 1}',
        checksum="repro-checksum",
        created_at_utc=DAY1,
    )

    DuckDBRunArtifactWriter(settings).persist(
        bundle=bundle,
        order_events=order_events,
        fill_events=fill_events,
        position_events=position_events,
        cash_events=cash_events,
        warnings=warnings,
        snapshots=snapshots,
        metrics=metrics,
        reproducibility_manifest=manifest,
    )

    repository = DuckDBRunArtifactRepository(settings)

    stored_bundle = repository.get_bundle(run_id)
    assert stored_bundle is not None
    assert stored_bundle.checksum == "checksum-1"

    orders_page = repository.list_order_events(run_id, limit=20, offset=0)
    assert orders_page.total == 1
    assert orders_page.items[0].order_id == "order-1"

    fills_page = repository.list_fill_events(run_id, limit=20, offset=0)
    assert fills_page.items[0].price == Decimal("100")

    positions_page = repository.list_position_events(run_id, limit=20, offset=0)
    assert positions_page.items[0].quantity == 5

    cash_page = repository.list_cash_events(run_id, limit=20, offset=0)
    assert cash_page.items[0].cash_after == Decimal("500")

    warnings_page = repository.list_warnings(run_id, limit=20, offset=0)
    assert warnings_page.items[0].code == "warn-1"

    snapshots_page = repository.list_portfolio_snapshots(run_id, limit=20, offset=0)
    assert snapshots_page.items[0].total_equity == Decimal("1000")

    stored_metrics = repository.list_metrics(run_id)
    assert stored_metrics[0].metric_key == "initial_equity"
    assert stored_metrics[0].value == Decimal("1000")
    assert stored_metrics[0].status == MetricStatus.AVAILABLE

    stored_manifest = repository.get_reproducibility_manifest(run_id)
    assert stored_manifest is not None
    assert stored_manifest.checksum == "repro-checksum"


def test_persist_failed_run_writes_no_snapshots_or_metrics(settings: Settings, run_id: str) -> None:
    bundle = _bundle(run_id, terminal_status="failed")
    warnings = [
        ExecutionWarning(
            code="warn-1", message="engine failed", instrument_id=None, timestamp_utc=None
        )
    ]
    manifest = ReproducibilityManifest(
        manifest_id="manifest-1",
        bundle_id=bundle.bundle_id,
        run_id=run_id,
        canonical_json='{"schema_version": 1}',
        checksum="repro-checksum",
        created_at_utc=DAY1,
    )

    DuckDBRunArtifactWriter(settings).persist(
        bundle=bundle,
        order_events=[],
        fill_events=[],
        position_events=[],
        cash_events=[],
        warnings=warnings,
        snapshots=[],
        metrics=[],
        reproducibility_manifest=manifest,
    )

    repository = DuckDBRunArtifactRepository(settings)
    assert repository.list_portfolio_snapshots(run_id, limit=20, offset=0).total == 0
    assert repository.list_metrics(run_id) == []
    assert repository.list_warnings(run_id, limit=20, offset=0).total == 1


def test_persist_rolls_back_on_failure(settings: Settings, run_id: str) -> None:
    bundle = _bundle(run_id)
    manifest = ReproducibilityManifest(
        manifest_id="manifest-1",
        bundle_id=bundle.bundle_id,
        run_id=run_id,
        canonical_json='{"schema_version": 1}',
        checksum="repro-checksum",
        created_at_utc=DAY1,
    )
    # A metric with a value that would violate the UNIQUE(bundle_id, metric_key)
    # constraint forces the transaction to fail after the bundle row is staged.
    duplicate_metrics = [
        MetricRecord(
            metric_key="initial_equity",
            status=MetricStatus.AVAILABLE,
            definition_version=1,
            calculation_input_json="{}",
            value=Decimal("1000"),
        ),
        MetricRecord(
            metric_key="initial_equity",
            status=MetricStatus.AVAILABLE,
            definition_version=1,
            calculation_input_json="{}",
            value=Decimal("2000"),
        ),
    ]
    writer = DuckDBRunArtifactWriter(settings)

    def _persist() -> None:
        writer.persist(
            bundle=bundle,
            order_events=[],
            fill_events=[],
            position_events=[],
            cash_events=[],
            warnings=[],
            snapshots=[],
            metrics=duplicate_metrics,
            reproducibility_manifest=manifest,
        )

    with pytest.raises(duckdb.Error):
        _persist()

    repository = DuckDBRunArtifactRepository(settings)
    assert repository.get_bundle(run_id) is None
