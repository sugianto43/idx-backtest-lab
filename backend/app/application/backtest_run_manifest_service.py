import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from app.application.errors import (
    DatasetNotFoundError,
    InstrumentNotFoundError,
    StrategySpecNotFoundError,
)
from app.application.ports.backtest_run_repository import BacktestRunRepository
from app.application.ports.dataset_repository import DatasetRepository
from app.application.ports.instrument_repository import InstrumentRepository
from app.application.ports.strategy_spec_repository import StrategySpecRepository
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
    RunManifestValidationError,
    StrategyRef,
    Universe,
)
from app.domain.backtest_run import BacktestRunStatus, RunManifest
from app.domain.checksum import canonical_json_bytes, compute_checksum
from app.domain.dataset import DatasetManifest

ENGINE_ADAPTER_NAME = "backtrader"
ENGINE_ADAPTER_VERSION = "unimplemented"


class DecimalFieldError(ValueError):
    def __init__(self, field: str) -> None:
        super().__init__(f"{field} must be a valid decimal string")
        self.field = field


def _parse_decimal(value: str, field: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise DecimalFieldError(field) from exc


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def _default_clock() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CreateRunManifestRequest:
    strategy_id: str
    strategy_version: int
    dataset_id: str
    instrument_ids: tuple[str, ...]
    start_date: date
    end_date: date
    capital_amount: str
    capital_currency: str
    position_sizing_fraction: str
    quantity_increment: str
    money_scale: int
    annualization_basis: int
    risk_free_rate: str


def _require_period_within_coverage(dataset: DatasetManifest, start: date, end: date) -> None:
    if dataset.coverage_start_date is None or dataset.coverage_end_date is None:
        raise RunManifestValidationError(
            "period_out_of_coverage", "dataset has no declared coverage range"
        )
    if start < dataset.coverage_start_date or end > dataset.coverage_end_date:
        raise RunManifestValidationError(
            "period_out_of_coverage", "requested period is outside the dataset's coverage range"
        )


def create_run_manifest(
    run_repository: BacktestRunRepository,
    strategy_repository: StrategySpecRepository,
    dataset_repository: DatasetRepository,
    instrument_repository: InstrumentRepository,
    request: CreateRunManifestRequest,
    *,
    id_factory: Callable[[], str] = _default_id_factory,
    clock: Callable[[], datetime] = _default_clock,
) -> RunManifest:
    strategy = strategy_repository.get(request.strategy_id, request.strategy_version)
    if strategy is None:
        raise StrategySpecNotFoundError(request.strategy_id, request.strategy_version)

    dataset = dataset_repository.get(request.dataset_id)
    if dataset is None:
        raise DatasetNotFoundError(request.dataset_id)

    for instrument_id in request.instrument_ids:
        if instrument_repository.get(instrument_id) is None:
            raise InstrumentNotFoundError(instrument_id)

    _require_period_within_coverage(dataset, request.start_date, request.end_date)

    manifest = RunManifestV1(
        run_id=id_factory(),
        strategy_ref=StrategyRef(
            strategy_id=strategy.strategy_id, version=strategy.version, checksum=strategy.checksum
        ),
        dataset_ref=DatasetRef(
            dataset_id=dataset.dataset_id,
            content_checksum=dataset.content_checksum or "",
        ),
        universe=Universe(instrument_ids=request.instrument_ids),
        period=Period(
            start_date=request.start_date,
            end_date=request.end_date,
            bar_interval=dataset.bar_interval,
        ),
        capital=Capital(
            amount=_parse_decimal(request.capital_amount, "capital.amount"),
            currency=request.capital_currency,
        ),
        execution=Execution(
            position_sizing=PositionSizing(
                fraction=_parse_decimal(
                    request.position_sizing_fraction, "execution.position_sizing.fraction"
                )
            ),
            rounding=Rounding(
                quantity_increment=_parse_decimal(
                    request.quantity_increment, "execution.rounding.quantity_increment"
                ),
                money_scale=request.money_scale,
            ),
        ),
        metrics=Metrics(
            annualization_basis=request.annualization_basis,
            risk_free_rate=_parse_decimal(request.risk_free_rate, "metrics.risk_free_rate"),
        ),
        engine_ref=EngineRef(
            adapter_name=ENGINE_ADAPTER_NAME, adapter_version=ENGINE_ADAPTER_VERSION
        ),
        created_at_utc=clock(),
    )

    canonical = manifest.to_canonical_dict()
    checksum = compute_checksum(canonical)
    canonical_json = canonical_json_bytes(canonical).decode("utf-8")

    run = RunManifest(
        run_id=manifest.run_id,
        dataset_id=dataset.dataset_id,
        strategy_spec_version=f"{strategy.strategy_id}@{strategy.version}",
        engine_version=ENGINE_ADAPTER_VERSION,
        configuration_json=canonical_json,
        status=BacktestRunStatus.CREATED,
        created_at_utc=manifest.created_at_utc,
        schema_version=manifest.schema_version,
        manifest_checksum=checksum,
        strategy_id=strategy.strategy_id,
        strategy_version=strategy.version,
    )
    return run_repository.create(run)
