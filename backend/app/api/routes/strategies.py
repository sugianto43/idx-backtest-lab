from fastapi import APIRouter, Depends, Query, status

from app.api.errors import AppError, NotFoundError
from app.api.schemas.strategies import (
    CreateStrategyRequest,
    SignalPolicySchema,
    SmaCrossoverParametersSchema,
    StrategySpecListResponse,
    StrategySpecResponse,
)
from app.application.strategy_spec_service import create_strategy_spec
from app.domain.strategy_spec import StrategySpecV1, StrategySpecValidationError
from app.infrastructure.db.strategy_spec_repository import DuckDBStrategySpecRepository
from app.infrastructure.settings import Settings, get_settings

v1_strategies_router = APIRouter(prefix="/api/v1")


class StrategySpecValidationHttpError(AppError):
    code = "validation_error"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "The strategy specification is invalid."


def _spec_response(spec: StrategySpecV1) -> StrategySpecResponse:
    return StrategySpecResponse(
        strategy_id=spec.strategy_id,
        version=spec.version,
        schema_version=spec.schema_version,
        name=spec.name,
        kind=spec.kind,
        parameters=SmaCrossoverParametersSchema(
            fast_window=spec.parameters.fast_window,
            slow_window=spec.parameters.slow_window,
            price_field=spec.parameters.price_field,  # type: ignore[arg-type]
        ),
        signal_policy=SignalPolicySchema(
            signal_time=spec.signal_policy.signal_time,  # type: ignore[arg-type]
            eligible_after_bars=spec.signal_policy.eligible_after_bars,
            long_only=spec.signal_policy.long_only,
        ),
        checksum=spec.checksum,
        created_at_utc=spec.created_at_utc,
    )


@v1_strategies_router.post(
    "/strategies", response_model=StrategySpecResponse, status_code=status.HTTP_201_CREATED
)
def create_strategy(
    payload: CreateStrategyRequest, settings: Settings = Depends(get_settings)
) -> StrategySpecResponse:
    repository = DuckDBStrategySpecRepository(settings)
    try:
        spec = create_strategy_spec(
            repository,
            name=payload.name,
            kind=payload.kind,
            fast_window=payload.parameters.fast_window,
            slow_window=payload.parameters.slow_window,
            price_field=payload.parameters.price_field,
            signal_time=payload.signal_policy.signal_time,
            eligible_after_bars=payload.signal_policy.eligible_after_bars,
            long_only=payload.signal_policy.long_only,
        )
    except StrategySpecValidationError as exc:
        raise StrategySpecValidationHttpError(
            details=[{"code": exc.code, "message": exc.message}]
        ) from exc
    return _spec_response(spec)


@v1_strategies_router.get("/strategies", response_model=StrategySpecListResponse)
def list_strategies(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> StrategySpecListResponse:
    page = DuckDBStrategySpecRepository(settings).list(limit=limit, offset=offset)
    return StrategySpecListResponse(
        items=[_spec_response(spec) for spec in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@v1_strategies_router.get(
    "/strategies/{strategy_id}/versions/{version}", response_model=StrategySpecResponse
)
def get_strategy_version(
    strategy_id: str, version: int, settings: Settings = Depends(get_settings)
) -> StrategySpecResponse:
    spec = DuckDBStrategySpecRepository(settings).get(strategy_id, version)
    if spec is None:
        raise NotFoundError()
    return _spec_response(spec)
