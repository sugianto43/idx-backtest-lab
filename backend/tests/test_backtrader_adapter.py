from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

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
    StrategyRef,
    Universe,
)
from app.domain.execution_result import OrderSide, OrderStatus, TerminalStatus
from app.domain.market_data import NormalizedBar
from app.domain.strategy_spec import SignalPolicy, SmaCrossoverParameters, StrategySpecV1
from app.infrastructure.engine.backtrader_adapter import BacktraderEngineAdapter

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _bars(closes: list[int], *, volumes: list[int] | None = None) -> list[NormalizedBar]:
    bars = []
    for i, c in enumerate(closes):
        close = Decimal(c)
        open_ = close - Decimal("0.5")
        volume = volumes[i] if volumes else 1000
        bars.append(
            NormalizedBar(
                bar_id=f"bar-{i}",
                dataset_id="ds-1",
                source_instrument_identifier="BBCA",
                timestamp_utc=BASE + timedelta(days=i),
                bar_interval="1d",
                open=open_,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=volume,
            )
        )
    return bars


def _strategy(**overrides: Any) -> StrategySpecV1:
    defaults: dict[str, Any] = {
        "strategy_id": "strat-1",
        "version": 1,
        "schema_version": 1,
        "name": "SMA 2/3",
        "kind": "sma_crossover",
        "parameters": SmaCrossoverParameters(fast_window=2, slow_window=3, price_field="close"),
        "signal_policy": SignalPolicy(
            signal_time="bar_close", eligible_after_bars=3, long_only=True
        ),
        "created_at_utc": BASE,
        "checksum": "sha256:aaa",
        "canonical_json": "{}",
    }
    defaults.update(overrides)
    return StrategySpecV1(**defaults)


def _manifest(*, num_bars: int, fraction: str = "0.50", capital: str = "1000000") -> RunManifestV1:
    return RunManifestV1(
        run_id="run-1",
        strategy_ref=StrategyRef(strategy_id="strat-1", version=1, checksum="sha256:aaa"),
        dataset_ref=DatasetRef(dataset_id="ds-1", content_checksum="sha256:bbb"),
        universe=Universe(instrument_ids=("ins-1",)),
        period=Period(
            start_date=BASE.date(),
            end_date=(BASE + timedelta(days=num_bars)).date(),
            bar_interval="1d",
        ),
        capital=Capital(amount=Decimal(capital), currency="IDR"),
        execution=Execution(
            position_sizing=PositionSizing(fraction=Decimal(fraction)),
            rounding=Rounding(quantity_increment=Decimal("1"), money_scale=2),
        ),
        metrics=Metrics(annualization_basis=252, risk_free_rate=Decimal("0")),
        engine_ref=EngineRef(adapter_name="backtrader", adapter_version="unimplemented"),
        created_at_utc=BASE,
    )


def _run_adapter(
    bars: list[NormalizedBar], manifest: RunManifestV1, strategy: StrategySpecV1
) -> Any:
    adapter = BacktraderEngineAdapter()
    counter = iter(range(10_000))
    return adapter.execute(
        manifest=manifest,
        manifest_checksum="sha256:manifest",
        strategy=strategy,
        instrument_id="ins-1",
        bars=bars,
        id_factory=lambda: f"id-{next(counter)}",
        clock=lambda: datetime.now(UTC),
    )


def test_smoke_fixture_proves_no_look_ahead_and_next_bar_open_fill() -> None:
    # Timeline (fast=2, slow=3, eligible_after_bars=3):
    #   bars 0-2 (closes 10,9,8): warm-up, no signal possible yet.
    #   bar 3 (close=12): fast SMA crosses above slow SMA -> entry INTENT created at bar 3's close.
    #   bar 4 (open=15.5): entry FILLS here, at the next bar's open -- never at bar 3's close (12).
    #   bars 4-5: still long, no new crossover.
    #   bar 6 (close=8): downward crossover -> exit INTENT created at bar 6's close.
    #   bar 7 (open=3.5): exit FILLS here, at the next bar's open.
    closes = [10, 9, 8, 12, 16, 20, 8, 4, 2, 2]
    bars = _bars(closes)
    manifest = _manifest(num_bars=len(closes))
    strategy = _strategy()

    result = _run_adapter(bars, manifest, strategy)

    assert result.terminal_status == TerminalStatus.COMPLETED
    assert result.failure_code is None
    assert len(result.order_events) == 2
    assert len(result.fill_events) == 2

    entry_order, exit_order = result.order_events
    entry_fill, exit_fill = result.fill_events

    # Entry: signal timestamp is bar 3's close-date; order created there, not before.
    assert entry_order.created_at_utc == bars[3].timestamp_utc
    assert entry_order.side == OrderSide.BUY
    assert entry_order.status == OrderStatus.FILLED

    # The fill must be at bar 4 (the NEXT bar), at its OPEN price -- never bar 3's close.
    assert entry_fill.filled_at_utc == bars[4].timestamp_utc
    assert entry_fill.price == bars[4].open
    assert entry_fill.price != bars[3].close

    # Exit: signal at bar 6's close, fill at bar 7's open.
    assert exit_order.created_at_utc == bars[6].timestamp_utc
    assert exit_order.side == OrderSide.SELL
    assert exit_fill.filled_at_utc == bars[7].timestamp_utc
    assert exit_fill.price == bars[7].open
    assert exit_fill.price != bars[6].close

    # Quantities and cash bookkeeping are internally consistent.
    assert entry_fill.quantity == exit_fill.quantity == entry_order.intended_quantity
    assert len(result.position_events) == 2
    assert result.position_events[0].quantity == entry_fill.quantity
    assert result.position_events[1].quantity == 0


def test_repeated_execution_with_same_inputs_is_event_equivalent() -> None:
    closes = [10, 9, 8, 12, 16, 20, 8, 4, 2, 2]
    manifest = _manifest(num_bars=len(closes))
    strategy = _strategy()

    result_a = _run_adapter(_bars(closes), manifest, strategy)
    result_b = _run_adapter(_bars(closes), manifest, strategy)

    def _semantic(result: Any) -> Any:
        return (
            result.terminal_status,
            result.failure_code,
            [(o.side, o.intended_quantity, o.status) for o in result.order_events],
            [(f.side, f.quantity, f.price) for f in result.fill_events],
        )

    assert _semantic(result_a) == _semantic(result_b)


def test_no_signal_before_slow_window_is_available() -> None:
    # Flat prices for the warm-up period: no crossover is even mathematically possible,
    # and eligible_after_bars gates any order before bar index 2 regardless.
    closes = [10, 10, 10]
    bars = _bars(closes)
    manifest = _manifest(num_bars=len(closes))
    strategy = _strategy()

    result = _run_adapter(bars, manifest, strategy)

    assert result.order_events == ()
    assert result.fill_events == ()


def test_missing_next_bar_for_eligible_signal_fails_the_run() -> None:
    # Crossover happens on the LAST bar of the feed -- there is no next bar to fill at.
    closes = [10, 9, 8, 20]
    bars = _bars(closes)
    manifest = _manifest(num_bars=len(closes))
    strategy = _strategy()

    result = _run_adapter(bars, manifest, strategy)

    assert result.terminal_status == TerminalStatus.FAILED
    assert result.failure_code == "missing_next_bar"


def test_zero_volume_fill_bar_produces_a_warning_not_a_rejection() -> None:
    closes = [10, 9, 8, 12, 16]
    bars = _bars(closes, volumes=[1000, 1000, 1000, 1000, 0])
    manifest = _manifest(num_bars=len(closes))
    strategy = _strategy()

    result = _run_adapter(bars, manifest, strategy)

    assert result.terminal_status == TerminalStatus.COMPLETED
    assert any(w.code == "zero_volume_fill" for w in result.warnings)
    assert len(result.fill_events) == 1


def test_metadata_records_adapter_and_checksums() -> None:
    closes = [10, 9, 8]
    bars = _bars(closes)
    manifest = _manifest(num_bars=len(closes))
    strategy = _strategy()

    result = _run_adapter(bars, manifest, strategy)

    assert result.metadata.adapter_name == "backtrader"
    assert result.metadata.manifest_checksum == "sha256:manifest"
    assert result.metadata.dataset_checksum == "sha256:bbb"
    assert result.metadata.started_at_utc <= result.metadata.finished_at_utc
