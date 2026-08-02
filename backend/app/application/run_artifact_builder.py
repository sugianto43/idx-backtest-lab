import uuid
from collections.abc import Callable
from datetime import datetime

from app.domain.backtest_manifest import RunManifestV1
from app.domain.backtest_run import RunManifest
from app.domain.checksum import canonical_json_bytes, compute_checksum
from app.domain.execution_result import ExecutionResult, TerminalStatus
from app.domain.market_data import NormalizedBar
from app.domain.run_artifact import (
    ARTIFACT_SCHEMA_VERSION,
    MetricRecord,
    PortfolioSnapshot,
    ReproducibilityManifest,
    RunArtifactBundle,
    build_portfolio_snapshots,
    compute_metrics,
)
from app.domain.strategy_spec import StrategySpecV1


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def build_provenance(
    *,
    run: RunManifest,
    manifest: RunManifestV1,
    strategy: StrategySpecV1,
    result: ExecutionResult,
) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "manifest_checksum": run.manifest_checksum,
        "strategy_id": strategy.strategy_id,
        "strategy_version": strategy.version,
        "strategy_checksum": strategy.checksum,
        "dataset_id": manifest.dataset_ref.dataset_id,
        "dataset_content_checksum": manifest.dataset_ref.content_checksum,
        "instrument_ids": list(manifest.universe.instrument_ids),
        "engine_adapter_name": result.metadata.adapter_name,
        "engine_adapter_version": result.metadata.adapter_version,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
    }


class RunArtifactBuild:
    def __init__(
        self,
        bundle: RunArtifactBundle,
        snapshots: list[PortfolioSnapshot],
        metrics: list[MetricRecord],
        reproducibility_manifest: ReproducibilityManifest,
    ) -> None:
        self.bundle = bundle
        self.snapshots = snapshots
        self.metrics = metrics
        self.reproducibility_manifest = reproducibility_manifest


def build_run_artifact(
    *,
    run: RunManifest,
    manifest: RunManifestV1,
    strategy: StrategySpecV1,
    bars: list[NormalizedBar],
    result: ExecutionResult,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime],
) -> RunArtifactBuild:
    provenance = build_provenance(run=run, manifest=manifest, strategy=strategy, result=result)

    if result.terminal_status == TerminalStatus.COMPLETED:
        snapshots = build_portfolio_snapshots(
            bars,
            result.cash_events,
            result.position_events,
            initial_cash=manifest.capital.amount,
            currency=manifest.capital.currency,
        )
        metrics = compute_metrics(
            initial_equity=manifest.capital.amount,
            snapshots=snapshots,
            fills=list(result.fill_events),
            annualization_basis=manifest.metrics.annualization_basis,
        )
    else:
        snapshots = []
        metrics = []

    event_count = (
        len(result.order_events)
        + len(result.fill_events)
        + len(result.position_events)
        + len(result.cash_events)
    )

    bundle_checksum_input = {
        "provenance": provenance,
        "terminal_status": result.terminal_status.value,
        "failure_code": result.failure_code,
        "event_count": event_count,
        "snapshot_count": len(snapshots),
        "metric_count": len(metrics),
    }
    bundle_id = id_factory()
    created_at = clock()

    bundle = RunArtifactBundle(
        bundle_id=bundle_id,
        run_id=run.run_id,
        artifact_schema_version=ARTIFACT_SCHEMA_VERSION,
        checksum=compute_checksum(bundle_checksum_input),
        terminal_status=result.terminal_status.value,
        provenance_json=canonical_json_bytes(provenance).decode("utf-8"),
        event_count=event_count,
        snapshot_count=len(snapshots),
        metric_count=len(metrics),
        created_at_utc=created_at,
    )

    repro_dict = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "run_id": run.run_id,
        "artifact_bundle_checksum": bundle.checksum,
        "run_manifest": manifest.to_canonical_dict(),
        "provenance": provenance,
        "metric_definition_version": 1,
        "event_count": event_count,
        "snapshot_count": len(snapshots),
        "warning_count": len(result.warnings),
    }
    reproducibility_manifest = ReproducibilityManifest(
        manifest_id=id_factory(),
        bundle_id=bundle_id,
        run_id=run.run_id,
        canonical_json=canonical_json_bytes(repro_dict).decode("utf-8"),
        checksum=compute_checksum(repro_dict),
        created_at_utc=created_at,
    )

    return RunArtifactBuild(
        bundle=bundle,
        snapshots=snapshots,
        metrics=metrics,
        reproducibility_manifest=reproducibility_manifest,
    )
