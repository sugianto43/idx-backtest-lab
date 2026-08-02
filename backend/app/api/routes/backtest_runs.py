import json

from fastapi import APIRouter, Depends, Query, status

from app.api.errors import AppError, NotFoundError
from app.api.schemas.backtest_runs import (
    BacktestRunListResponse,
    BacktestRunResponse,
    CreateBacktestRunRequest,
)
from app.application.backtest_run_manifest_service import (
    CreateRunManifestRequest,
    DecimalFieldError,
    create_run_manifest,
)
from app.application.errors import (
    DatasetNotFoundError,
    InstrumentNotFoundError,
    StrategySpecNotFoundError,
)
from app.domain.backtest_manifest import RunManifestValidationError
from app.domain.backtest_run import RunManifest
from app.infrastructure.db.backtest_run_repository import DuckDBBacktestRunRepository
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.instrument_repository import DuckDBInstrumentRepository
from app.infrastructure.db.strategy_spec_repository import DuckDBStrategySpecRepository
from app.infrastructure.settings import Settings, get_settings

v1_backtest_runs_router = APIRouter(prefix="/api/v1")


class RunManifestValidationHttpError(AppError):
    code = "validation_error"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "The run manifest is invalid."


def _run_response(run: RunManifest) -> BacktestRunResponse:
    return BacktestRunResponse(
        run_id=run.run_id,
        dataset_id=run.dataset_id,
        strategy_id=run.strategy_id,
        strategy_version=run.strategy_version,
        schema_version=run.schema_version,
        status=run.status.value,
        manifest_checksum=run.manifest_checksum,
        manifest=json.loads(run.configuration_json),
        warning_count=run.warning_count,
        created_at_utc=run.created_at_utc,
    )


@v1_backtest_runs_router.post(
    "/backtest-runs", response_model=BacktestRunResponse, status_code=status.HTTP_201_CREATED
)
def create_backtest_run(
    payload: CreateBacktestRunRequest, settings: Settings = Depends(get_settings)
) -> BacktestRunResponse:
    try:
        run = create_run_manifest(
            DuckDBBacktestRunRepository(settings),
            DuckDBStrategySpecRepository(settings),
            DuckDBDatasetRepository(settings),
            DuckDBInstrumentRepository(settings),
            CreateRunManifestRequest(
                strategy_id=payload.strategy_id,
                strategy_version=payload.strategy_version,
                dataset_id=payload.dataset_id,
                instrument_ids=tuple(payload.instrument_ids),
                start_date=payload.start_date,
                end_date=payload.end_date,
                capital_amount=payload.capital_amount,
                capital_currency=payload.capital_currency,
                position_sizing_fraction=payload.position_sizing_fraction,
                quantity_increment=payload.quantity_increment,
                money_scale=payload.money_scale,
                annualization_basis=payload.annualization_basis,
                risk_free_rate=payload.risk_free_rate,
            ),
        )
    except (StrategySpecNotFoundError, DatasetNotFoundError, InstrumentNotFoundError) as exc:
        raise NotFoundError() from exc
    except (RunManifestValidationError, DecimalFieldError) as exc:
        code = getattr(exc, "code", "invalid_manifest")
        raise RunManifestValidationHttpError(details=[{"code": code, "message": str(exc)}]) from exc
    return _run_response(run)


@v1_backtest_runs_router.get("/backtest-runs", response_model=BacktestRunListResponse)
def list_backtest_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> BacktestRunListResponse:
    page = DuckDBBacktestRunRepository(settings).list(limit=limit, offset=offset)
    return BacktestRunListResponse(
        items=[_run_response(run) for run in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@v1_backtest_runs_router.get("/backtest-runs/{run_id}", response_model=BacktestRunResponse)
def get_backtest_run(
    run_id: str, settings: Settings = Depends(get_settings)
) -> BacktestRunResponse:
    run = DuckDBBacktestRunRepository(settings).get(run_id)
    if run is None:
        raise NotFoundError()
    return _run_response(run)
