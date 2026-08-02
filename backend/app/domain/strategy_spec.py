from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

ALLOWED_PRICE_FIELDS = frozenset({"close"})
SUPPORTED_STRATEGY_KINDS = frozenset(
    {"sma_crossover", "rsi_threshold", "macd_crossover", "bollinger_breakout"}
)
STRATEGY_SCHEMA_VERSION = 1


class StrategySpecValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class SmaCrossoverParameters:
    fast_window: int
    slow_window: int
    price_field: str

    def __post_init__(self) -> None:
        if self.fast_window < 1:
            raise StrategySpecValidationError(
                "invalid_parameters", "fast_window must be a positive integer"
            )
        if self.slow_window < 1:
            raise StrategySpecValidationError(
                "invalid_parameters", "slow_window must be a positive integer"
            )
        if self.fast_window >= self.slow_window:
            raise StrategySpecValidationError(
                "invalid_parameters", "fast_window must be less than slow_window"
            )
        if self.price_field not in ALLOWED_PRICE_FIELDS:
            raise StrategySpecValidationError(
                "invalid_parameters",
                f"price_field must be one of {sorted(ALLOWED_PRICE_FIELDS)}",
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "fast_window": self.fast_window,
            "slow_window": self.slow_window,
            "price_field": self.price_field,
        }

    def required_warmup_bars(self) -> int:
        return self.slow_window


@dataclass(frozen=True, slots=True)
class RsiThresholdParameters:
    period: int
    oversold_threshold: int
    overbought_threshold: int
    price_field: str

    def __post_init__(self) -> None:
        if self.period < 2:
            raise StrategySpecValidationError(
                "invalid_parameters", "period must be an integer of at least 2"
            )
        if not (0 < self.oversold_threshold < self.overbought_threshold < 100):
            raise StrategySpecValidationError(
                "invalid_parameters",
                "oversold_threshold and overbought_threshold must satisfy "
                "0 < oversold_threshold < overbought_threshold < 100",
            )
        if self.price_field not in ALLOWED_PRICE_FIELDS:
            raise StrategySpecValidationError(
                "invalid_parameters",
                f"price_field must be one of {sorted(ALLOWED_PRICE_FIELDS)}",
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "oversold_threshold": self.oversold_threshold,
            "overbought_threshold": self.overbought_threshold,
            "price_field": self.price_field,
        }

    def required_warmup_bars(self) -> int:
        return self.period + 1


@dataclass(frozen=True, slots=True)
class MacdCrossoverParameters:
    fast_period: int
    slow_period: int
    signal_period: int
    price_field: str

    def __post_init__(self) -> None:
        if self.fast_period < 1:
            raise StrategySpecValidationError(
                "invalid_parameters", "fast_period must be a positive integer"
            )
        if self.slow_period <= self.fast_period:
            raise StrategySpecValidationError(
                "invalid_parameters", "slow_period must be greater than fast_period"
            )
        if self.signal_period < 1:
            raise StrategySpecValidationError(
                "invalid_parameters", "signal_period must be a positive integer"
            )
        if self.price_field not in ALLOWED_PRICE_FIELDS:
            raise StrategySpecValidationError(
                "invalid_parameters",
                f"price_field must be one of {sorted(ALLOWED_PRICE_FIELDS)}",
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
            "price_field": self.price_field,
        }

    def required_warmup_bars(self) -> int:
        return self.slow_period + self.signal_period


@dataclass(frozen=True, slots=True)
class BollingerBreakoutParameters:
    period: int
    num_std_dev: int
    price_field: str

    def __post_init__(self) -> None:
        if self.period < 2:
            raise StrategySpecValidationError(
                "invalid_parameters", "period must be an integer of at least 2"
            )
        if not (1 <= self.num_std_dev <= 4):
            raise StrategySpecValidationError(
                "invalid_parameters", "num_std_dev must be an integer between 1 and 4"
            )
        if self.price_field not in ALLOWED_PRICE_FIELDS:
            raise StrategySpecValidationError(
                "invalid_parameters",
                f"price_field must be one of {sorted(ALLOWED_PRICE_FIELDS)}",
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "period": self.period,
            "num_std_dev": self.num_std_dev,
            "price_field": self.price_field,
        }

    def required_warmup_bars(self) -> int:
        return self.period


StrategyParameters = (
    SmaCrossoverParameters
    | RsiThresholdParameters
    | MacdCrossoverParameters
    | BollingerBreakoutParameters
)

_KIND_TO_PARAMETERS_TYPE: dict[str, type] = {
    "sma_crossover": SmaCrossoverParameters,
    "rsi_threshold": RsiThresholdParameters,
    "macd_crossover": MacdCrossoverParameters,
    "bollinger_breakout": BollingerBreakoutParameters,
}


def build_parameters(kind: str, raw: Mapping[str, object]) -> StrategyParameters:
    if kind not in SUPPORTED_STRATEGY_KINDS:
        raise StrategySpecValidationError(
            "unsupported_kind", f"kind must be one of {sorted(SUPPORTED_STRATEGY_KINDS)}"
        )
    parameters_type = _KIND_TO_PARAMETERS_TYPE[kind]
    try:
        return parameters_type(**raw)  # type: ignore[no-any-return]
    except TypeError as exc:
        raise StrategySpecValidationError(
            "invalid_parameters", f"parameters do not match kind {kind!r}: {exc}"
        ) from exc


@dataclass(frozen=True, slots=True)
class SignalPolicy:
    signal_time: str
    eligible_after_bars: int
    long_only: bool

    def __post_init__(self) -> None:
        if self.signal_time != "bar_close":
            raise StrategySpecValidationError(
                "invalid_signal_policy", "signal_time must be 'bar_close' in v1"
            )
        if self.eligible_after_bars < 1:
            raise StrategySpecValidationError(
                "invalid_signal_policy", "eligible_after_bars must be a positive integer"
            )
        if not self.long_only:
            raise StrategySpecValidationError(
                "invalid_signal_policy", "long_only must be true in v1 (no short selling)"
            )

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "signal_time": self.signal_time,
            "eligible_after_bars": self.eligible_after_bars,
            "long_only": self.long_only,
        }


@dataclass(frozen=True, slots=True)
class StrategySpecV1:
    strategy_id: str
    version: int
    schema_version: int
    name: str
    kind: str
    parameters: StrategyParameters
    signal_policy: SignalPolicy
    created_at_utc: datetime
    checksum: str
    canonical_json: str

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise StrategySpecValidationError("invalid_spec", "strategy_id must not be empty")
        if self.version < 1:
            raise StrategySpecValidationError("invalid_spec", "version must be a positive integer")
        if self.schema_version != STRATEGY_SCHEMA_VERSION:
            raise StrategySpecValidationError(
                "unsupported_schema_version",
                f"schema_version must be {STRATEGY_SCHEMA_VERSION}",
            )
        if not self.name.strip():
            raise StrategySpecValidationError("invalid_spec", "name must not be empty")
        if self.kind not in SUPPORTED_STRATEGY_KINDS:
            raise StrategySpecValidationError(
                "unsupported_kind", f"kind must be one of {sorted(SUPPORTED_STRATEGY_KINDS)}"
            )
        if type(self.parameters) is not _KIND_TO_PARAMETERS_TYPE[self.kind]:
            raise StrategySpecValidationError(
                "kind_parameters_mismatch",
                f"parameters type does not match kind {self.kind!r}",
            )
        if self.signal_policy.eligible_after_bars < self.parameters.required_warmup_bars():
            raise StrategySpecValidationError(
                "invalid_signal_policy",
                "eligible_after_bars must be greater than or equal to the strategy's "
                "required warm-up bar count",
            )
        if self.created_at_utc.tzinfo is None:
            raise StrategySpecValidationError(
                "invalid_spec", "created_at_utc must be timezone-aware"
            )
        if not self.checksum:
            raise StrategySpecValidationError("invalid_spec", "checksum must not be empty")
        if not self.canonical_json:
            raise StrategySpecValidationError("invalid_spec", "canonical_json must not be empty")

    def to_canonical_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "strategy_id": self.strategy_id,
            "version": self.version,
            "name": self.name,
            "kind": self.kind,
            "parameters": self.parameters.to_canonical_dict(),
            "signal_policy": self.signal_policy.to_canonical_dict(),
            "created_at_utc": _format_utc(self.created_at_utc),
        }


def _format_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
