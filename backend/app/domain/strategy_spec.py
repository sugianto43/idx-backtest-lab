from dataclasses import dataclass
from datetime import datetime

ALLOWED_PRICE_FIELDS = frozenset({"close"})
SUPPORTED_STRATEGY_KINDS = frozenset({"sma_crossover"})
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
    parameters: SmaCrossoverParameters
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
        if self.signal_policy.eligible_after_bars < self.parameters.slow_window:
            raise StrategySpecValidationError(
                "invalid_signal_policy",
                "eligible_after_bars must be greater than or equal to slow_window",
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
