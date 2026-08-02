from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

RUN_MANIFEST_SCHEMA_VERSION = 1
CORPORATE_ACTION_TREATMENT = "dataset_as_declared_no_event_adjustment"
UNRESOLVED_IDENTIFIER_POLICY = "reject"
SIGNAL_TIME = "bar_close"
FILL_TIME = "next_bar_open"
MISSING_NEXT_BAR_POLICY = "reject"
POSITION_SIZING_KIND = "fixed_fraction"
NONE_KIND = "none"
IGNORE_WITH_WARNING_KIND = "ignore_with_warning"


class RunManifestValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _require_positive_decimal(value: Decimal, field: str) -> None:
    if not value.is_finite() or value <= 0:
        raise RunManifestValidationError(
            "invalid_manifest", f"{field} must be a finite positive decimal"
        )


def _decimal_str(value: Decimal) -> str:
    return format(value, "f")


def _format_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class StrategyRef:
    strategy_id: str
    version: int
    checksum: str

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise RunManifestValidationError(
                "invalid_manifest", "strategy_ref.strategy_id must not be empty"
            )
        if self.version < 1:
            raise RunManifestValidationError(
                "invalid_manifest", "strategy_ref.version must be positive"
            )
        if not self.checksum:
            raise RunManifestValidationError(
                "invalid_manifest", "strategy_ref.checksum must not be empty"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {"strategy_id": self.strategy_id, "version": self.version, "checksum": self.checksum}


@dataclass(frozen=True, slots=True)
class DatasetRef:
    dataset_id: str
    content_checksum: str

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise RunManifestValidationError(
                "invalid_manifest", "dataset_ref.dataset_id must not be empty"
            )
        if not self.content_checksum:
            raise RunManifestValidationError(
                "invalid_manifest", "dataset_ref.content_checksum must not be empty"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {"dataset_id": self.dataset_id, "content_checksum": self.content_checksum}


@dataclass(frozen=True, slots=True)
class Universe:
    instrument_ids: tuple[str, ...]
    unresolved_identifier_policy: str = UNRESOLVED_IDENTIFIER_POLICY

    def __post_init__(self) -> None:
        if not self.instrument_ids:
            raise RunManifestValidationError(
                "empty_universe", "universe.instrument_ids must not be empty"
            )
        if len(set(self.instrument_ids)) != len(self.instrument_ids):
            raise RunManifestValidationError(
                "invalid_manifest", "universe.instrument_ids must not contain duplicates"
            )
        if self.unresolved_identifier_policy != UNRESOLVED_IDENTIFIER_POLICY:
            raise RunManifestValidationError(
                "unsupported_feature", "unresolved_identifier_policy must be 'reject' in v1"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "instrument_ids": list(self.instrument_ids),
            "unresolved_identifier_policy": self.unresolved_identifier_policy,
        }


@dataclass(frozen=True, slots=True)
class Period:
    start_date: date
    end_date: date
    bar_interval: str

    def __post_init__(self) -> None:
        if self.start_date >= self.end_date:
            raise RunManifestValidationError(
                "invalid_period", "period.start_date must be before period.end_date"
            )
        if not self.bar_interval.strip():
            raise RunManifestValidationError(
                "invalid_manifest", "period.bar_interval must not be empty"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "bar_interval": self.bar_interval,
        }


@dataclass(frozen=True, slots=True)
class Capital:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        _require_positive_decimal(self.amount, "capital.amount")
        if not self.currency.strip():
            raise RunManifestValidationError(
                "invalid_manifest", "capital.currency must not be empty"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {"amount": _decimal_str(self.amount), "currency": self.currency}


@dataclass(frozen=True, slots=True)
class SignalAndFill:
    signal_time: str = SIGNAL_TIME
    fill_time: str = FILL_TIME
    missing_next_bar_policy: str = MISSING_NEXT_BAR_POLICY

    def __post_init__(self) -> None:
        if self.signal_time != SIGNAL_TIME:
            raise RunManifestValidationError(
                "unsupported_feature", "signal_time must be 'bar_close' in v1"
            )
        if self.fill_time != FILL_TIME:
            raise RunManifestValidationError(
                "unsupported_feature", "fill_time must be 'next_bar_open' in v1"
            )
        if self.missing_next_bar_policy != MISSING_NEXT_BAR_POLICY:
            raise RunManifestValidationError(
                "unsupported_feature", "missing_next_bar_policy must be 'reject' in v1"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "signal_time": self.signal_time,
            "fill_time": self.fill_time,
            "missing_next_bar_policy": self.missing_next_bar_policy,
        }


@dataclass(frozen=True, slots=True)
class PositionSizing:
    fraction: Decimal
    kind: str = POSITION_SIZING_KIND

    def __post_init__(self) -> None:
        if self.kind != POSITION_SIZING_KIND:
            raise RunManifestValidationError(
                "unsupported_feature", "position_sizing.kind must be 'fixed_fraction' in v1"
            )
        if not self.fraction.is_finite() or not (Decimal("0") < self.fraction <= Decimal("1")):
            raise RunManifestValidationError(
                "invalid_manifest", "position_sizing.fraction must be in the range (0, 1]"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "fraction": _decimal_str(self.fraction)}


@dataclass(frozen=True, slots=True)
class KindSetting:
    kind: str

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise RunManifestValidationError("invalid_manifest", "kind must not be empty")

    def to_canonical_dict(self) -> dict[str, object]:
        return {"kind": self.kind}


@dataclass(frozen=True, slots=True)
class Rounding:
    quantity_increment: Decimal
    money_scale: int

    def __post_init__(self) -> None:
        _require_positive_decimal(self.quantity_increment, "rounding.quantity_increment")
        if self.money_scale < 0:
            raise RunManifestValidationError(
                "invalid_manifest", "rounding.money_scale must not be negative"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "quantity_increment": _decimal_str(self.quantity_increment),
            "money_scale": self.money_scale,
        }


@dataclass(frozen=True, slots=True)
class Execution:
    position_sizing: PositionSizing
    rounding: Rounding
    commission: KindSetting = KindSetting(kind=NONE_KIND)
    tax: KindSetting = KindSetting(kind=NONE_KIND)
    slippage: KindSetting = KindSetting(kind=NONE_KIND)
    liquidity: KindSetting = KindSetting(kind=IGNORE_WITH_WARNING_KIND)
    price_limit: KindSetting = KindSetting(kind=IGNORE_WITH_WARNING_KIND)

    def __post_init__(self) -> None:
        if self.commission.kind != NONE_KIND:
            raise RunManifestValidationError(
                "unsupported_feature", "commission.kind must be 'none' in v1"
            )
        if self.tax.kind != NONE_KIND:
            raise RunManifestValidationError("unsupported_feature", "tax.kind must be 'none' in v1")
        if self.slippage.kind != NONE_KIND:
            raise RunManifestValidationError(
                "unsupported_feature", "slippage.kind must be 'none' in v1"
            )
        if self.liquidity.kind != IGNORE_WITH_WARNING_KIND:
            raise RunManifestValidationError(
                "unsupported_feature", "liquidity.kind must be 'ignore_with_warning' in v1"
            )
        if self.price_limit.kind != IGNORE_WITH_WARNING_KIND:
            raise RunManifestValidationError(
                "unsupported_feature", "price_limit.kind must be 'ignore_with_warning' in v1"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "position_sizing": self.position_sizing.to_canonical_dict(),
            "commission": self.commission.to_canonical_dict(),
            "tax": self.tax.to_canonical_dict(),
            "slippage": self.slippage.to_canonical_dict(),
            "liquidity": self.liquidity.to_canonical_dict(),
            "price_limit": self.price_limit.to_canonical_dict(),
            "rounding": self.rounding.to_canonical_dict(),
        }


@dataclass(frozen=True, slots=True)
class Metrics:
    annualization_basis: int
    risk_free_rate: Decimal

    def __post_init__(self) -> None:
        if self.annualization_basis < 1:
            raise RunManifestValidationError(
                "invalid_manifest", "metrics.annualization_basis must be a positive integer"
            )
        if not self.risk_free_rate.is_finite() or self.risk_free_rate < 0:
            raise RunManifestValidationError(
                "invalid_manifest", "metrics.risk_free_rate must be a non-negative finite decimal"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "annualization_basis": self.annualization_basis,
            "risk_free_rate": _decimal_str(self.risk_free_rate),
        }


@dataclass(frozen=True, slots=True)
class EngineRef:
    adapter_name: str
    adapter_version: str

    def __post_init__(self) -> None:
        if not self.adapter_name.strip():
            raise RunManifestValidationError(
                "invalid_manifest", "engine_ref.adapter_name must not be empty"
            )
        if not self.adapter_version.strip():
            raise RunManifestValidationError(
                "invalid_manifest", "engine_ref.adapter_version must not be empty"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {"adapter_name": self.adapter_name, "adapter_version": self.adapter_version}


@dataclass(frozen=True, slots=True)
class RunManifestV1:
    run_id: str
    strategy_ref: StrategyRef
    dataset_ref: DatasetRef
    universe: Universe
    period: Period
    capital: Capital
    execution: Execution
    metrics: Metrics
    engine_ref: EngineRef
    created_at_utc: datetime
    schema_version: int = RUN_MANIFEST_SCHEMA_VERSION
    signal_and_fill: SignalAndFill = SignalAndFill()
    corporate_action_treatment: str = CORPORATE_ACTION_TREATMENT
    benchmark: KindSetting = KindSetting(kind=NONE_KIND)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise RunManifestValidationError("invalid_manifest", "run_id must not be empty")
        if self.schema_version != RUN_MANIFEST_SCHEMA_VERSION:
            raise RunManifestValidationError(
                "unsupported_schema_version",
                f"schema_version must be {RUN_MANIFEST_SCHEMA_VERSION}",
            )
        if self.corporate_action_treatment != CORPORATE_ACTION_TREATMENT:
            raise RunManifestValidationError(
                "unsupported_feature",
                f"corporate_action_treatment must be '{CORPORATE_ACTION_TREATMENT}' in v1",
            )
        if self.benchmark.kind != NONE_KIND:
            raise RunManifestValidationError(
                "unsupported_feature", "benchmark.kind must be 'none' in v1"
            )
        if self.created_at_utc.tzinfo is None:
            raise RunManifestValidationError(
                "invalid_manifest", "created_at_utc must be timezone-aware"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "strategy_ref": self.strategy_ref.to_canonical_dict(),
            "dataset_ref": self.dataset_ref.to_canonical_dict(),
            "universe": self.universe.to_canonical_dict(),
            "period": self.period.to_canonical_dict(),
            "capital": self.capital.to_canonical_dict(),
            "signal_and_fill": self.signal_and_fill.to_canonical_dict(),
            "corporate_action_treatment": self.corporate_action_treatment,
            "execution": self.execution.to_canonical_dict(),
            "benchmark": self.benchmark.to_canonical_dict(),
            "metrics": self.metrics.to_canonical_dict(),
            "engine_ref": self.engine_ref.to_canonical_dict(),
            "created_at_utc": _format_utc(self.created_at_utc),
        }


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_run_manifest(data: dict[str, Any]) -> RunManifestV1:
    strategy_ref_data = data["strategy_ref"]
    dataset_ref_data = data["dataset_ref"]
    universe_data = data["universe"]
    period_data = data["period"]
    capital_data = data["capital"]
    signal_and_fill_data = data["signal_and_fill"]
    execution_data = data["execution"]
    metrics_data = data["metrics"]
    engine_ref_data = data["engine_ref"]
    position_sizing_data = execution_data["position_sizing"]
    rounding_data = execution_data["rounding"]

    return RunManifestV1(
        run_id=data["run_id"],
        schema_version=data["schema_version"],
        strategy_ref=StrategyRef(**strategy_ref_data),
        dataset_ref=DatasetRef(**dataset_ref_data),
        universe=Universe(
            instrument_ids=tuple(universe_data["instrument_ids"]),
            unresolved_identifier_policy=universe_data["unresolved_identifier_policy"],
        ),
        period=Period(
            start_date=date.fromisoformat(period_data["start_date"]),
            end_date=date.fromisoformat(period_data["end_date"]),
            bar_interval=period_data["bar_interval"],
        ),
        capital=Capital(amount=Decimal(capital_data["amount"]), currency=capital_data["currency"]),
        signal_and_fill=SignalAndFill(**signal_and_fill_data),
        corporate_action_treatment=data["corporate_action_treatment"],
        execution=Execution(
            position_sizing=PositionSizing(
                fraction=Decimal(position_sizing_data["fraction"]),
                kind=position_sizing_data["kind"],
            ),
            commission=KindSetting(**execution_data["commission"]),
            tax=KindSetting(**execution_data["tax"]),
            slippage=KindSetting(**execution_data["slippage"]),
            liquidity=KindSetting(**execution_data["liquidity"]),
            price_limit=KindSetting(**execution_data["price_limit"]),
            rounding=Rounding(
                quantity_increment=Decimal(rounding_data["quantity_increment"]),
                money_scale=rounding_data["money_scale"],
            ),
        ),
        benchmark=KindSetting(**data["benchmark"]),
        metrics=Metrics(
            annualization_basis=metrics_data["annualization_basis"],
            risk_free_rate=Decimal(metrics_data["risk_free_rate"]),
        ),
        engine_ref=EngineRef(**engine_ref_data),
        created_at_utc=_parse_utc(data["created_at_utc"]),
    )
