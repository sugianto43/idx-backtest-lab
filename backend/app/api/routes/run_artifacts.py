import json
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.errors import NotFoundError
from app.api.schemas.run_artifacts import (
    ComparisonCompatibilityResponse,
    MetricSchema,
    PaginatedEventsResponse,
    PortfolioSnapshotSchema,
    PortfolioSnapshotsResponse,
    ReproducibilityManifestResponse,
    RunArtifactsResponse,
    RunMetricsResponse,
    RunSummaryResponse,
)
from app.domain.backtest_manifest import parse_run_manifest
from app.domain.execution_result import (
    CashEvent,
    ExecutionWarning,
    FillEvent,
    OrderEvent,
    PositionEvent,
)
from app.domain.run_artifact import MetricRecord, PortfolioSnapshot
from app.infrastructure.db.backtest_run_repository import DuckDBBacktestRunRepository
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.run_artifact_repository import DuckDBRunArtifactRepository
from app.infrastructure.settings import Settings, get_settings

v1_run_artifacts_router = APIRouter(prefix="/api/v1")


def _metric_schema(metric: MetricRecord) -> MetricSchema:
    return MetricSchema(
        metric_key=metric.metric_key,
        status=metric.status.value,
        value=str(metric.value) if metric.value is not None else None,
        reason=metric.reason,
        definition_version=metric.definition_version,
    )


def _snapshot_schema(snapshot: PortfolioSnapshot) -> PortfolioSnapshotSchema:
    return PortfolioSnapshotSchema(
        sequence=snapshot.sequence,
        timestamp_utc=snapshot.timestamp_utc,
        cash=str(snapshot.cash),
        holdings_value=str(snapshot.holdings_value),
        total_equity=str(snapshot.total_equity),
        currency=snapshot.currency,
        status=snapshot.status.value,
        reason=snapshot.reason,
    )


def _order_dict(event: OrderEvent) -> dict[str, Any]:
    return {
        "order_id": event.order_id,
        "instrument_id": event.instrument_id,
        "side": event.side.value,
        "created_at_utc": event.created_at_utc.isoformat(),
        "intended_quantity": event.intended_quantity,
        "status": event.status.value,
        "rejection_reason": event.rejection_reason,
    }


def _fill_dict(event: FillEvent) -> dict[str, Any]:
    return {
        "order_id": event.order_id,
        "instrument_id": event.instrument_id,
        "side": event.side.value,
        "filled_at_utc": event.filled_at_utc.isoformat(),
        "quantity": event.quantity,
        "price": str(event.price),
        "currency": event.currency,
        "commission": str(event.commission),
        "tax": str(event.tax),
        "slippage": str(event.slippage),
    }


def _position_dict(event: PositionEvent) -> dict[str, Any]:
    return {
        "timestamp_utc": event.timestamp_utc.isoformat(),
        "instrument_id": event.instrument_id,
        "quantity": event.quantity,
        "average_cost": str(event.average_cost),
        "reason": event.reason,
    }


def _cash_dict(event: CashEvent) -> dict[str, Any]:
    return {
        "timestamp_utc": event.timestamp_utc.isoformat(),
        "currency": event.currency,
        "cash_before": str(event.cash_before),
        "cash_after": str(event.cash_after),
        "reason": event.reason,
    }


def _warning_dict(event: ExecutionWarning) -> dict[str, Any]:
    return {
        "code": event.code,
        "message": event.message,
        "instrument_id": event.instrument_id,
        "timestamp_utc": event.timestamp_utc.isoformat() if event.timestamp_utc else None,
    }


@v1_run_artifacts_router.get("/backtest-runs/{run_id}/summary", response_model=RunSummaryResponse)
def get_run_summary(run_id: str, settings: Settings = Depends(get_settings)) -> RunSummaryResponse:
    run = DuckDBBacktestRunRepository(settings).get(run_id)
    if run is None:
        raise NotFoundError()

    bundle = DuckDBRunArtifactRepository(settings).get_bundle(run_id)
    metrics = DuckDBRunArtifactRepository(settings).list_metrics(run_id)

    return RunSummaryResponse(
        run_id=run.run_id,
        status=run.status.value,
        terminal_status=bundle.terminal_status if bundle else None,
        manifest_checksum=run.manifest_checksum,
        artifact_schema_version=bundle.artifact_schema_version if bundle else None,
        artifact_checksum=bundle.checksum if bundle else None,
        event_count=bundle.event_count if bundle else None,
        snapshot_count=bundle.snapshot_count if bundle else None,
        warning_count=run.warning_count,
        metrics=[_metric_schema(m) for m in metrics],
    )


@v1_run_artifacts_router.get(
    "/backtest-runs/{run_id}/artifacts", response_model=RunArtifactsResponse
)
def get_run_artifacts(
    run_id: str, settings: Settings = Depends(get_settings)
) -> RunArtifactsResponse:
    if DuckDBBacktestRunRepository(settings).get(run_id) is None:
        raise NotFoundError()
    bundle = DuckDBRunArtifactRepository(settings).get_bundle(run_id)
    if bundle is None:
        raise NotFoundError()

    return RunArtifactsResponse(
        bundle_id=bundle.bundle_id,
        run_id=bundle.run_id,
        artifact_schema_version=bundle.artifact_schema_version,
        checksum=bundle.checksum,
        terminal_status=bundle.terminal_status,
        provenance=json.loads(bundle.provenance_json),
        event_count=bundle.event_count,
        snapshot_count=bundle.snapshot_count,
        metric_count=bundle.metric_count,
        created_at_utc=bundle.created_at_utc,
        sections={
            "events": f"/api/v1/backtest-runs/{run_id}/events",
            "portfolio_snapshots": f"/api/v1/backtest-runs/{run_id}/portfolio-snapshots",
            "metrics": f"/api/v1/backtest-runs/{run_id}/metrics",
            "reproducibility_manifest": f"/api/v1/backtest-runs/{run_id}/reproducibility-manifest",
        },
    )


@v1_run_artifacts_router.get(
    "/backtest-runs/{run_id}/events", response_model=PaginatedEventsResponse
)
def list_run_events(
    run_id: str,
    type: str = Query(..., pattern="^(order|fill|position|cash|warning)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> PaginatedEventsResponse:
    if DuckDBBacktestRunRepository(settings).get(run_id) is None:
        raise NotFoundError()

    repository = DuckDBRunArtifactRepository(settings)
    items: list[dict[str, Any]]
    total: int
    if type == "order":
        order_page = repository.list_order_events(run_id, limit=limit, offset=offset)
        items, total = [_order_dict(e) for e in order_page.items], order_page.total
    elif type == "fill":
        fill_page = repository.list_fill_events(run_id, limit=limit, offset=offset)
        items, total = [_fill_dict(e) for e in fill_page.items], fill_page.total
    elif type == "position":
        position_page = repository.list_position_events(run_id, limit=limit, offset=offset)
        items, total = [_position_dict(e) for e in position_page.items], position_page.total
    elif type == "cash":
        cash_page = repository.list_cash_events(run_id, limit=limit, offset=offset)
        items, total = [_cash_dict(e) for e in cash_page.items], cash_page.total
    else:
        warning_page = repository.list_warnings(run_id, limit=limit, offset=offset)
        items, total = [_warning_dict(e) for e in warning_page.items], warning_page.total

    return PaginatedEventsResponse(type=type, items=items, total=total, limit=limit, offset=offset)


@v1_run_artifacts_router.get(
    "/backtest-runs/{run_id}/portfolio-snapshots", response_model=PortfolioSnapshotsResponse
)
def list_portfolio_snapshots(
    run_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> PortfolioSnapshotsResponse:
    if DuckDBBacktestRunRepository(settings).get(run_id) is None:
        raise NotFoundError()
    page = DuckDBRunArtifactRepository(settings).list_portfolio_snapshots(
        run_id, limit=limit, offset=offset
    )
    return PortfolioSnapshotsResponse(
        items=[_snapshot_schema(s) for s in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@v1_run_artifacts_router.get("/backtest-runs/{run_id}/metrics", response_model=RunMetricsResponse)
def list_run_metrics(run_id: str, settings: Settings = Depends(get_settings)) -> RunMetricsResponse:
    if DuckDBBacktestRunRepository(settings).get(run_id) is None:
        raise NotFoundError()
    metrics = DuckDBRunArtifactRepository(settings).list_metrics(run_id)
    return RunMetricsResponse(items=[_metric_schema(m) for m in metrics])


@v1_run_artifacts_router.get(
    "/backtest-runs/{run_id}/reproducibility-manifest",
    response_model=ReproducibilityManifestResponse,
)
def get_reproducibility_manifest(
    run_id: str, settings: Settings = Depends(get_settings)
) -> ReproducibilityManifestResponse:
    if DuckDBBacktestRunRepository(settings).get(run_id) is None:
        raise NotFoundError()
    manifest = DuckDBRunArtifactRepository(settings).get_reproducibility_manifest(run_id)
    if manifest is None:
        raise NotFoundError()

    return ReproducibilityManifestResponse(
        filename=f"reproducibility-manifest-{run_id}.json",
        content_type="application/json",
        checksum=manifest.checksum,
        manifest=json.loads(manifest.canonical_json),
    )


@v1_run_artifacts_router.get(
    "/backtest-runs/{run_id}/comparison-compatibility",
    response_model=ComparisonCompatibilityResponse,
)
def get_comparison_compatibility(
    run_id: str,
    other_run_id: str = Query(...),
    settings: Settings = Depends(get_settings),
) -> ComparisonCompatibilityResponse:
    run_repository = DuckDBBacktestRunRepository(settings)
    run_a = run_repository.get(run_id)
    run_b = run_repository.get(other_run_id)
    if run_a is None or run_b is None:
        raise NotFoundError()

    reasons: list[str] = []
    manifest_a = parse_run_manifest(json.loads(run_a.configuration_json))
    manifest_b = parse_run_manifest(json.loads(run_b.configuration_json))

    if run_a.schema_version != run_b.schema_version:
        reasons.append("Runs use different manifest schema versions.")
    if manifest_a.capital.currency != manifest_b.capital.currency:
        reasons.append("Runs use different capital currencies.")
    if manifest_a.period.bar_interval != manifest_b.period.bar_interval:
        reasons.append("Runs use different bar intervals.")
    if manifest_a.metrics.annualization_basis != manifest_b.metrics.annualization_basis:
        reasons.append("Runs use different annualization bases.")

    dataset_repository = DuckDBDatasetRepository(settings)
    dataset_a = dataset_repository.get(manifest_a.dataset_ref.dataset_id)
    dataset_b = dataset_repository.get(manifest_b.dataset_ref.dataset_id)
    if (
        dataset_a is not None
        and dataset_b is not None
        and dataset_a.adjustment_policy != dataset_b.adjustment_policy
    ):
        reasons.append("Runs use datasets with different adjustment policies.")

    artifact_repository = DuckDBRunArtifactRepository(settings)
    bundle_a = artifact_repository.get_bundle(run_id)
    bundle_b = artifact_repository.get_bundle(other_run_id)
    if bundle_a is None or bundle_b is None:
        reasons.append("One or both runs have no completed artifact bundle.")
    elif bundle_a.artifact_schema_version != bundle_b.artifact_schema_version:
        reasons.append("Runs use different artifact schema versions.")

    return ComparisonCompatibilityResponse(compatible=len(reasons) == 0, reasons=reasons)
