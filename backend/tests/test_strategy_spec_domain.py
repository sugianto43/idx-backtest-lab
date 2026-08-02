from datetime import UTC, datetime
from typing import Any

import pytest

from app.domain.checksum import compute_checksum
from app.domain.strategy_spec import (
    BollingerBreakoutParameters,
    ComboCondition,
    MacdCrossoverParameters,
    MultiIndicatorComboParameters,
    RsiThresholdParameters,
    SignalPolicy,
    SmaCrossoverParameters,
    StrategySpecV1,
    StrategySpecValidationError,
    build_parameters,
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


def test_rsi_parameters_reject_out_of_order_thresholds() -> None:
    with pytest.raises(StrategySpecValidationError):
        RsiThresholdParameters(
            period=14, oversold_threshold=70, overbought_threshold=30, price_field="close"
        )


def test_rsi_parameters_reject_short_period() -> None:
    with pytest.raises(StrategySpecValidationError):
        RsiThresholdParameters(
            period=1, oversold_threshold=30, overbought_threshold=70, price_field="close"
        )


def test_rsi_parameters_required_warmup_is_period_plus_one() -> None:
    parameters = RsiThresholdParameters(
        period=14, oversold_threshold=30, overbought_threshold=70, price_field="close"
    )
    assert parameters.required_warmup_bars() == 15


def test_macd_parameters_reject_slow_period_not_greater_than_fast() -> None:
    with pytest.raises(StrategySpecValidationError):
        MacdCrossoverParameters(
            fast_period=26, slow_period=12, signal_period=9, price_field="close"
        )


def test_macd_parameters_required_warmup_is_slow_plus_signal() -> None:
    parameters = MacdCrossoverParameters(
        fast_period=12, slow_period=26, signal_period=9, price_field="close"
    )
    assert parameters.required_warmup_bars() == 35


def test_bollinger_parameters_reject_std_dev_out_of_range() -> None:
    with pytest.raises(StrategySpecValidationError):
        BollingerBreakoutParameters(period=20, num_std_dev=5, price_field="close")


def test_bollinger_parameters_required_warmup_is_period() -> None:
    parameters = BollingerBreakoutParameters(period=20, num_std_dev=2, price_field="close")
    assert parameters.required_warmup_bars() == 20


def test_build_parameters_rejects_unsupported_kind() -> None:
    with pytest.raises(StrategySpecValidationError):
        build_parameters("does_not_exist", {})


def test_build_parameters_dispatches_by_kind() -> None:
    parameters = build_parameters(
        "rsi_threshold",
        {
            "period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
            "price_field": "close",
        },
    )
    assert isinstance(parameters, RsiThresholdParameters)


def test_spec_rejects_kind_parameters_mismatch() -> None:
    with pytest.raises(StrategySpecValidationError):
        _spec(
            kind="rsi_threshold",
            parameters=SmaCrossoverParameters(fast_window=10, slow_window=30, price_field="close"),
            signal_policy=SignalPolicy(
                signal_time="bar_close", eligible_after_bars=30, long_only=True
            ),
        )


def _sma_condition() -> ComboCondition:
    return ComboCondition(
        kind="sma_crossover",
        parameters=SmaCrossoverParameters(fast_window=10, slow_window=30, price_field="close"),
    )


def _rsi_condition() -> ComboCondition:
    return ComboCondition(
        kind="rsi_threshold",
        parameters=RsiThresholdParameters(
            period=14, oversold_threshold=30, overbought_threshold=70, price_field="close"
        ),
    )


def _macd_condition() -> ComboCondition:
    return ComboCondition(
        kind="macd_crossover",
        parameters=MacdCrossoverParameters(
            fast_period=12, slow_period=26, signal_period=9, price_field="close"
        ),
    )


def test_combo_condition_rejects_non_base_kind() -> None:
    with pytest.raises(StrategySpecValidationError):
        ComboCondition(
            kind="multi_indicator_combo",
            parameters=SmaCrossoverParameters(fast_window=10, slow_window=30, price_field="close"),
        )


def test_combo_condition_rejects_kind_parameters_mismatch() -> None:
    with pytest.raises(StrategySpecValidationError):
        ComboCondition(
            kind="rsi_threshold",
            parameters=SmaCrossoverParameters(fast_window=10, slow_window=30, price_field="close"),
        )


def test_combo_parameters_reject_fewer_than_two_conditions() -> None:
    with pytest.raises(StrategySpecValidationError):
        MultiIndicatorComboParameters(conditions=(_sma_condition(),))


def test_combo_parameters_reject_more_than_three_conditions() -> None:
    with pytest.raises(StrategySpecValidationError):
        MultiIndicatorComboParameters(
            conditions=(
                _sma_condition(),
                _rsi_condition(),
                _macd_condition(),
                _sma_condition(),
            )
        )


def test_combo_parameters_reject_duplicate_condition_kinds() -> None:
    with pytest.raises(StrategySpecValidationError):
        MultiIndicatorComboParameters(conditions=(_sma_condition(), _sma_condition()))


def test_combo_parameters_required_warmup_is_the_max_across_conditions() -> None:
    parameters = MultiIndicatorComboParameters(conditions=(_sma_condition(), _rsi_condition()))
    assert parameters.required_warmup_bars() == max(30, 15)


def test_build_parameters_dispatches_combo_kind() -> None:
    parameters = build_parameters(
        "multi_indicator_combo",
        {
            "conditions": [
                {
                    "kind": "sma_crossover",
                    "parameters": {"fast_window": 10, "slow_window": 30, "price_field": "close"},
                },
                {
                    "kind": "rsi_threshold",
                    "parameters": {
                        "period": 14,
                        "oversold_threshold": 30,
                        "overbought_threshold": 70,
                        "price_field": "close",
                    },
                },
            ]
        },
    )
    assert isinstance(parameters, MultiIndicatorComboParameters)
    assert len(parameters.conditions) == 2


def test_build_parameters_combo_rejects_unknown_condition_kind() -> None:
    with pytest.raises(StrategySpecValidationError):
        build_parameters(
            "multi_indicator_combo",
            {"conditions": [{"kind": "does_not_exist", "parameters": {}}]},
        )


def test_build_parameters_combo_rejects_nested_combo_condition() -> None:
    with pytest.raises(StrategySpecValidationError):
        build_parameters(
            "multi_indicator_combo",
            {"conditions": [{"kind": "multi_indicator_combo", "parameters": {"conditions": []}}]},
        )


def test_spec_rejects_combo_with_fewer_than_two_conditions() -> None:
    with pytest.raises(StrategySpecValidationError):
        _spec(
            kind="multi_indicator_combo",
            parameters=MultiIndicatorComboParameters(conditions=(_sma_condition(),)),
        )
