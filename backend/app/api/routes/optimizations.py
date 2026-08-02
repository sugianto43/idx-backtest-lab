import json

from fastapi import APIRouter, Depends, Query, status

from app.api.errors import AppError, NotFoundError
from app.api.schemas.optimizations import (
    CandidateSummaryResponse,
    CreateOptimizationRequest,
    HoldoutResultResponse,
    OptimizationCandidatesResponse,
    OptimizationDetailResponse,
    OptimizationListResponse,
    OptimizationSummaryResponse,
)
from app.application.errors import (
    ApplicationError,
    DatasetNotFoundError,
    InstrumentNotFoundError,
    OptimizationInvalidTransitionError,
    OptimizationNotEligibleError,
    OptimizationNotFoundError,
)
from app.application.execute_optimization_service import (
    OptimizationExecutionPorts,
    execute_optimization,
)
from app.application.optimization_manifest_service import (
    CreateOptimizationRequest as CreateOptimizationServiceRequest,
)
from app.application.optimization_manifest_service import (
    OptimizationDecimalFieldError,
    create_optimization,
)
from app.domain.optimization import (
    OptimizationCandidate,
    OptimizationManifest,
    OptimizationStatus,
    OptimizationValidationError,
)
from app.infrastructure.db.backtest_run_repository import DuckDBBacktestRunRepository
from app.infrastructure.db.bar_snapshot_repository import DuckDBBarSnapshotRepository
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.instrument_repository import DuckDBInstrumentRepository
from app.infrastructure.db.optimization_repository import DuckDBOptimizationRepository
from app.infrastructure.db.run_artifact_repository import DuckDBRunArtifactRepository
from app.infrastructure.db.run_artifact_writer import DuckDBRunArtifactWriter
from app.infrastructure.db.strategy_spec_repository import DuckDBStrategySpecRepository
from app.infrastructure.engine.backtrader_adapter import BacktraderEngineAdapter
from app.infrastructure.settings import Settings, get_settings

v1_optimizations_router = APIRouter(prefix="/api/v1")


class OptimizationValidationHttpError(AppError):
    code = "validation_error"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "The optimization manifest is invalid."


class OptimizationNotEligibleHttpError(AppError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The optimization is not eligible to execute in its current status."


def _summary_response(manifest: OptimizationManifest) -> OptimizationSummaryResponse:
    return OptimizationSummaryResponse(
        optimization_id=manifest.optimization_id,
        status=manifest.status.value,
        dataset_id=manifest.dataset_id,
        instrument_id=manifest.instrument_id,
        base_strategy_name=manifest.base_strategy_name,
        objective_metric_key=manifest.objective_metric_key,
        candidate_count=manifest.candidate_count,
        rejected_count=manifest.rejected_count,
        max_candidate_count=manifest.max_candidate_count,
        failure_code=manifest.failure_code,
        created_at_utc=manifest.created_at_utc,
        started_at_utc=manifest.started_at_utc,
        finished_at_utc=manifest.finished_at_utc,
    )


def _detail_response(manifest: OptimizationManifest) -> OptimizationDetailResponse:
    is_completed = manifest.status == OptimizationStatus.COMPLETED
    holdout = HoldoutResultResponse(
        sealed=not is_completed,
        run_id=manifest.holdout_run_id if is_completed else None,
        objective_status=(
            manifest.holdout_objective_status.value
            if is_completed and manifest.holdout_objective_status
            else None
        ),
        objective_value=(
            str(manifest.holdout_objective_value)
            if is_completed and manifest.holdout_objective_value is not None
            else None
        ),
        objective_reason=manifest.holdout_objective_reason if is_completed else None,
    )
    return OptimizationDetailResponse(
        **_summary_response(manifest).model_dump(),
        schema_version=manifest.schema_version,
        checksum=manifest.checksum,
        fast_window_grid=list(manifest.fast_window_grid),
        slow_window_grid=list(manifest.slow_window_grid),
        train_start=manifest.train_start,
        train_end=manifest.train_end,
        validation_start=manifest.validation_start,
        validation_end=manifest.validation_end,
        holdout_start=manifest.holdout_start,
        holdout_end=manifest.holdout_end,
        tie_break_rule=manifest.tie_break_rule,
        manifest=json.loads(manifest.manifest_json),
        selected_candidate_id=manifest.selected_candidate_id,
        selection_reason=manifest.selection_reason,
        selection_audit=(
            json.loads(manifest.selection_audit_json) if manifest.selection_audit_json else None
        ),
        selected_at_utc=manifest.selected_at_utc,
        holdout=holdout,
    )


def _candidate_response(candidate: OptimizationCandidate) -> CandidateSummaryResponse:
    return CandidateSummaryResponse(
        candidate_id=candidate.candidate_id,
        sequence=candidate.sequence,
        fast_window=candidate.fast_window,
        slow_window=candidate.slow_window,
        status=candidate.status.value,
        rejection_reason=candidate.rejection_reason,
        strategy_id=candidate.strategy_id,
        strategy_version=candidate.strategy_version,
        train_run_id=candidate.train_run_id,
        validation_run_id=candidate.validation_run_id,
        objective_status=candidate.objective_status.value if candidate.objective_status else None,
        objective_value=(
            str(candidate.objective_value) if candidate.objective_value is not None else None
        ),
        objective_reason=candidate.objective_reason,
        warning_count=candidate.warning_count,
        created_at_utc=candidate.created_at_utc,
    )


@v1_optimizations_router.post(
    "/optimizations", response_model=OptimizationDetailResponse, status_code=status.HTTP_201_CREATED
)
def create_optimization_endpoint(
    payload: CreateOptimizationRequest, settings: Settings = Depends(get_settings)
) -> OptimizationDetailResponse:
    try:
        manifest = create_optimization(
            DuckDBOptimizationRepository(settings),
            DuckDBDatasetRepository(settings),
            DuckDBInstrumentRepository(settings),
            DuckDBBarSnapshotRepository(settings),
            CreateOptimizationServiceRequest(
                dataset_id=payload.dataset_id,
                instrument_id=payload.instrument_id,
                base_strategy_name=payload.base_strategy_name,
                fast_windows=payload.fast_windows,
                slow_windows=payload.slow_windows,
                train_start=payload.train_start,
                train_end=payload.train_end,
                validation_start=payload.validation_start,
                validation_end=payload.validation_end,
                holdout_start=payload.holdout_start,
                holdout_end=payload.holdout_end,
                capital_amount=payload.capital_amount,
                capital_currency=payload.capital_currency,
                position_sizing_fraction=payload.position_sizing_fraction,
                quantity_increment=payload.quantity_increment,
                money_scale=payload.money_scale,
                annualization_basis=payload.annualization_basis,
                risk_free_rate=payload.risk_free_rate,
                objective_metric_key=payload.objective_metric_key,
            ),
            max_candidate_count=settings.optimization_max_candidate_count,
        )
    except (DatasetNotFoundError, InstrumentNotFoundError) as exc:
        raise NotFoundError() from exc
    except (OptimizationValidationError, OptimizationDecimalFieldError) as exc:
        code = getattr(exc, "code", "invalid_manifest")
        raise OptimizationValidationHttpError(
            details=[{"code": code, "message": str(exc)}]
        ) from exc
    return _detail_response(manifest)


@v1_optimizations_router.get("/optimizations", response_model=OptimizationListResponse)
def list_optimizations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> OptimizationListResponse:
    page = DuckDBOptimizationRepository(settings).list(limit=limit, offset=offset)
    return OptimizationListResponse(
        items=[_summary_response(manifest) for manifest in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@v1_optimizations_router.get(
    "/optimizations/{optimization_id}", response_model=OptimizationDetailResponse
)
def get_optimization(
    optimization_id: str, settings: Settings = Depends(get_settings)
) -> OptimizationDetailResponse:
    manifest = DuckDBOptimizationRepository(settings).get(optimization_id)
    if manifest is None:
        raise NotFoundError()
    return _detail_response(manifest)


@v1_optimizations_router.get(
    "/optimizations/{optimization_id}/candidates", response_model=OptimizationCandidatesResponse
)
def list_optimization_candidates(
    optimization_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> OptimizationCandidatesResponse:
    repository = DuckDBOptimizationRepository(settings)
    if repository.get(optimization_id) is None:
        raise NotFoundError()
    page = repository.list_candidates(optimization_id, limit=limit, offset=offset)
    return OptimizationCandidatesResponse(
        items=[_candidate_response(candidate) for candidate in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@v1_optimizations_router.post(
    "/optimizations/{optimization_id}:execute", response_model=OptimizationDetailResponse
)
def execute_optimization_endpoint(
    optimization_id: str, settings: Settings = Depends(get_settings)
) -> OptimizationDetailResponse:
    ports = OptimizationExecutionPorts(
        optimization_repository=DuckDBOptimizationRepository(settings),
        strategy_repository=DuckDBStrategySpecRepository(settings),
        dataset_repository=DuckDBDatasetRepository(settings),
        instrument_repository=DuckDBInstrumentRepository(settings),
        run_repository=DuckDBBacktestRunRepository(settings),
        bar_snapshot_repository=DuckDBBarSnapshotRepository(settings),
        run_artifact_repository=DuckDBRunArtifactRepository(settings),
        engine=BacktraderEngineAdapter(),
        artifact_writer=DuckDBRunArtifactWriter(settings),
    )
    try:
        manifest = execute_optimization(ports, optimization_id)
    except OptimizationNotFoundError as exc:
        raise NotFoundError() from exc
    except (OptimizationNotEligibleError, OptimizationInvalidTransitionError) as exc:
        raise OptimizationNotEligibleHttpError(details=[{"message": str(exc)}]) from exc
    except ApplicationError as exc:
        raise AppError(details=[{"message": str(exc)}]) from exc
    return _detail_response(manifest)
