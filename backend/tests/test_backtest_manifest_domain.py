from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.domain.backtest_manifest import (
    Capital,
    DatasetRef,
    EngineRef,
    Execution,
    KindSetting,
    Metrics,
    Period,
    PositionSizing,
    Rounding,
    RunManifestV1,
    RunManifestValidationError,
    StrategyRef,
    Universe,
)
from app.domain.checksum import compute_checksum


def _manifest(**overrides: Any) -> RunManifestV1:
    defaults: dict[str, Any] = {
        "run_id": "run-1",
        "strategy_ref": StrategyRef(strategy_id="strat-1", version=1, checksum="sha256:aaa"),
        "dataset_ref": DatasetRef(dataset_id="ds-1", content_checksum="sha256:bbb"),
        "universe": Universe(instrument_ids=("ins-1",)),
        "period": Period(
            start_date=date(2020, 1, 1), end_date=date(2020, 12, 31), bar_interval="1d"
        ),
        "capital": Capital(amount=Decimal("100000000.00"), currency="IDR"),
        "execution": Execution(
            position_sizing=PositionSizing(fraction=Decimal("1.00")),
            rounding=Rounding(quantity_increment=Decimal("1"), money_scale=2),
        ),
        "metrics": Metrics(annualization_basis=252, risk_free_rate=Decimal("0.00")),
        "engine_ref": EngineRef(adapter_name="backtrader", adapter_version="unimplemented"),
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return RunManifestV1(**defaults)


def test_valid_manifest_constructs() -> None:
    assert _manifest().schema_version == 1


def test_universe_rejects_empty_instrument_ids() -> None:
    with pytest.raises(RunManifestValidationError):
        Universe(instrument_ids=())


def test_universe_rejects_duplicate_instrument_ids() -> None:
    with pytest.raises(RunManifestValidationError):
        Universe(instrument_ids=("ins-1", "ins-1"))


def test_period_rejects_end_before_start() -> None:
    with pytest.raises(RunManifestValidationError):
        Period(start_date=date(2020, 12, 31), end_date=date(2020, 1, 1), bar_interval="1d")


def test_capital_rejects_non_positive_amount() -> None:
    with pytest.raises(RunManifestValidationError):
        Capital(amount=Decimal("0"), currency="IDR")


def test_position_sizing_rejects_fraction_above_one() -> None:
    with pytest.raises(RunManifestValidationError):
        PositionSizing(fraction=Decimal("1.5"))


def test_position_sizing_rejects_unsupported_kind() -> None:
    with pytest.raises(RunManifestValidationError):
        PositionSizing(fraction=Decimal("1.00"), kind="kelly")


def test_execution_rejects_non_none_commission() -> None:
    with pytest.raises(RunManifestValidationError):
        Execution(
            position_sizing=PositionSizing(fraction=Decimal("1.00")),
            rounding=Rounding(quantity_increment=Decimal("1"), money_scale=2),
            commission=KindSetting(kind="fixed_per_trade"),
        )


def test_execution_rejects_non_ignore_liquidity() -> None:
    with pytest.raises(RunManifestValidationError):
        Execution(
            position_sizing=PositionSizing(fraction=Decimal("1.00")),
            rounding=Rounding(quantity_increment=Decimal("1"), money_scale=2),
            liquidity=KindSetting(kind="realistic"),
        )


def test_manifest_rejects_unsupported_benchmark() -> None:
    with pytest.raises(RunManifestValidationError):
        _manifest(benchmark=KindSetting(kind="ihsg"))


def test_manifest_rejects_unsupported_corporate_action_treatment() -> None:
    with pytest.raises(RunManifestValidationError):
        _manifest(corporate_action_treatment="split_adjusted")


def test_metrics_rejects_negative_risk_free_rate() -> None:
    with pytest.raises(RunManifestValidationError):
        Metrics(annualization_basis=252, risk_free_rate=Decimal("-0.01"))


def test_equivalent_manifests_produce_identical_checksum() -> None:
    manifest_a = _manifest()
    manifest_b = _manifest(run_id="run-1")

    assert compute_checksum(manifest_a.to_canonical_dict()) == compute_checksum(
        manifest_b.to_canonical_dict()
    )


def test_materially_different_capital_produces_different_checksum() -> None:
    manifest_a = _manifest()
    manifest_b = _manifest(capital=Capital(amount=Decimal("50000000.00"), currency="IDR"))

    assert compute_checksum(manifest_a.to_canonical_dict()) != compute_checksum(
        manifest_b.to_canonical_dict()
    )


def test_canonical_dict_preserves_exact_decimal_string() -> None:
    manifest = _manifest(capital=Capital(amount=Decimal("100000000.00"), currency="IDR"))

    assert manifest.to_canonical_dict()["capital"]["amount"] == "100000000.00"  # type: ignore[index]
