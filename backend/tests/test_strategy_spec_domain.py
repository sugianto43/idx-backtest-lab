from datetime import UTC, datetime
from typing import Any

import pytest

from app.domain.checksum import compute_checksum
from app.domain.strategy_spec import (
    SignalPolicy,
    SmaCrossoverParameters,
    StrategySpecV1,
    StrategySpecValidationError,
)


def test_parameters_reject_fast_window_not_less_than_slow_window() -> None:
    with pytest.raises(StrategySpecValidationError):
        SmaCrossoverParameters(fast_window=30, slow_window=30, price_field="close")


def test_parameters_reject_non_positive_window() -> None:
    with pytest.raises(StrategySpecValidationError):
        SmaCrossoverParameters(fast_window=0, slow_window=10, price_field="close")


def test_parameters_reject_unsupported_price_field() -> None:
    with pytest.raises(StrategySpecValidationError):
        SmaCrossoverParameters(fast_window=10, slow_window=30, price_field="vwap")


def test_signal_policy_rejects_non_bar_close_signal_time() -> None:
    with pytest.raises(StrategySpecValidationError):
        SignalPolicy(signal_time="bar_open", eligible_after_bars=30, long_only=True)


def test_signal_policy_rejects_short_selling() -> None:
    with pytest.raises(StrategySpecValidationError):
        SignalPolicy(signal_time="bar_close", eligible_after_bars=30, long_only=False)


def _spec(**overrides: Any) -> StrategySpecV1:
    parameters = overrides.pop(
        "parameters", SmaCrossoverParameters(fast_window=10, slow_window=30, price_field="close")
    )
    signal_policy = overrides.pop(
        "signal_policy",
        SignalPolicy(signal_time="bar_close", eligible_after_bars=30, long_only=True),
    )
    defaults: dict[str, Any] = {
        "strategy_id": "strat-1",
        "version": 1,
        "schema_version": 1,
        "name": "SMA crossover 10/30",
        "kind": "sma_crossover",
        "parameters": parameters,
        "signal_policy": signal_policy,
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "checksum": "sha256:deadbeef",
        "canonical_json": "{}",
    }
    defaults.update(overrides)
    return StrategySpecV1(**defaults)


def test_valid_spec_constructs() -> None:
    assert _spec().kind == "sma_crossover"


def test_spec_rejects_eligible_after_bars_less_than_slow_window() -> None:
    with pytest.raises(StrategySpecValidationError):
        _spec(
            signal_policy=SignalPolicy(
                signal_time="bar_close", eligible_after_bars=10, long_only=True
            )
        )


def test_spec_rejects_unsupported_kind() -> None:
    with pytest.raises(StrategySpecValidationError):
        _spec(kind="rsi_reversion")


def test_spec_rejects_unsupported_schema_version() -> None:
    with pytest.raises(StrategySpecValidationError):
        _spec(schema_version=2)


def test_equivalent_canonical_payloads_produce_identical_checksum() -> None:
    spec_a = _spec()
    spec_b = _spec(strategy_id="strat-1")

    assert compute_checksum(spec_a.to_canonical_dict()) == compute_checksum(
        spec_b.to_canonical_dict()
    )


def test_materially_different_parameters_produce_different_checksum() -> None:
    spec_a = _spec()
    spec_b = _spec(
        parameters=SmaCrossoverParameters(fast_window=5, slow_window=30, price_field="close")
    )

    assert compute_checksum(spec_a.to_canonical_dict()) != compute_checksum(
        spec_b.to_canonical_dict()
    )
