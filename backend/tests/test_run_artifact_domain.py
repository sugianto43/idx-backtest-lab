from datetime import UTC, datetime
from decimal import Decimal

from app.domain.execution_result import CashEvent, FillEvent, OrderSide, PositionEvent
from app.domain.market_data import NormalizedBar
from app.domain.run_artifact import (
    MetricStatus,
    SnapshotValuationStatus,
    build_portfolio_snapshots,
    compute_fifo_realized_pnl,
    compute_metrics,
)

DAY1 = datetime(2026, 1, 1, tzinfo=UTC)
DAY2 = datetime(2026, 1, 2, tzinfo=UTC)
DAY3 = datetime(2026, 1, 3, tzinfo=UTC)


def _bar(timestamp: datetime, close: Decimal) -> NormalizedBar:
    return NormalizedBar(
        bar_id=f"bar-{timestamp.date()}",
        dataset_id="dataset-1",
        source_instrument_identifier="BBCA",
        timestamp_utc=timestamp,
        bar_interval="1d",
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
    )


BARS = [_bar(DAY1, Decimal("100")), _bar(DAY2, Decimal("110")), _bar(DAY3, Decimal("90"))]

CASH_EVENTS = (
    CashEvent(
        timestamp_utc=DAY1,
        currency="IDR",
        cash_before=Decimal("1000"),
        cash_after=Decimal("500"),
        reason="buy_fill",
    ),
    CashEvent(
        timestamp_utc=DAY2,
        currency="IDR",
        cash_before=Decimal("500"),
        cash_after=Decimal("1050"),
        reason="sell_fill",
    ),
)
POSITION_EVENTS = (
    PositionEvent(
        timestamp_utc=DAY1,
        instrument_id="BBCA",
        quantity=5,
        average_cost=Decimal("100"),
        reason="buy_fill",
    ),
    PositionEvent(
        timestamp_utc=DAY2,
        instrument_id="BBCA",
        quantity=0,
        average_cost=Decimal("0"),
        reason="sell_fill",
    ),
)
FILLS = [
    FillEvent(
        order_id="order-1",
        instrument_id="BBCA",
        side=OrderSide.BUY,
        filled_at_utc=DAY1,
        quantity=5,
        price=Decimal("100"),
        currency="IDR",
        commission=Decimal("0"),
        tax=Decimal("0"),
        slippage=Decimal("0"),
    ),
    FillEvent(
        order_id="order-2",
        instrument_id="BBCA",
        side=OrderSide.SELL,
        filled_at_utc=DAY2,
        quantity=5,
        price=Decimal("110"),
        currency="IDR",
        commission=Decimal("0"),
        tax=Decimal("0"),
        slippage=Decimal("0"),
    ),
]


def test_build_portfolio_snapshots_values_cash_and_holdings_at_bar_close() -> None:
    snapshots = build_portfolio_snapshots(
        BARS, CASH_EVENTS, POSITION_EVENTS, initial_cash=Decimal("1000"), currency="IDR"
    )

    assert [s.total_equity for s in snapshots] == [
        Decimal("1000"),
        Decimal("1050"),
        Decimal("1050"),
    ]
    assert snapshots[0].holdings_value == Decimal("500")
    assert snapshots[1].holdings_value == Decimal("0")
    assert all(s.status == SnapshotValuationStatus.VALID for s in snapshots)


def test_build_portfolio_snapshots_with_no_events_uses_initial_cash_only() -> None:
    snapshots = build_portfolio_snapshots(
        BARS, (), (), initial_cash=Decimal("1000"), currency="IDR"
    )

    assert all(s.cash == Decimal("1000") for s in snapshots)
    assert all(s.holdings_value == Decimal("0") for s in snapshots)


def test_compute_fifo_realized_pnl_matches_oldest_lot_first() -> None:
    realized = compute_fifo_realized_pnl(FILLS)

    assert realized == [Decimal("50")]


def test_compute_fifo_realized_pnl_subtracts_costs_from_sell_fill() -> None:
    fills = [
        FillEvent(
            order_id="order-1",
            instrument_id="BBCA",
            side=OrderSide.BUY,
            filled_at_utc=DAY1,
            quantity=5,
            price=Decimal("100"),
            currency="IDR",
            commission=Decimal("0"),
            tax=Decimal("0"),
            slippage=Decimal("0"),
        ),
        FillEvent(
            order_id="order-2",
            instrument_id="BBCA",
            side=OrderSide.SELL,
            filled_at_utc=DAY2,
            quantity=5,
            price=Decimal("110"),
            currency="IDR",
            commission=Decimal("2"),
            tax=Decimal("1"),
            slippage=Decimal("0.5"),
        ),
    ]

    realized = compute_fifo_realized_pnl(fills)

    assert realized == [Decimal("46.5")]


def test_compute_metrics_produces_expected_values_for_hand_calculated_fixture() -> None:
    snapshots = build_portfolio_snapshots(
        BARS, CASH_EVENTS, POSITION_EVENTS, initial_cash=Decimal("1000"), currency="IDR"
    )

    metrics = {
        m.metric_key: m
        for m in compute_metrics(
            initial_equity=Decimal("1000"),
            snapshots=snapshots,
            fills=FILLS,
            annualization_basis=252,
        )
    }

    assert metrics["initial_equity"].value == Decimal("1000")
    assert metrics["final_equity"].value == Decimal("1050")
    assert metrics["total_return"].value == Decimal("0.05")
    assert metrics["annualized_return"].status == MetricStatus.AVAILABLE
    assert metrics["max_drawdown"].value == Decimal("0")
    assert metrics["trade_count"].value == Decimal("1")
    assert metrics["win_rate"].value == Decimal("1")
    assert metrics["realized_pnl"].value == Decimal("50")
    assert metrics["exposure_time_ratio"].value == Decimal("1") / Decimal("3")


def test_compute_metrics_reports_not_available_when_no_snapshots() -> None:
    metrics = {
        m.metric_key: m
        for m in compute_metrics(
            initial_equity=Decimal("1000"), snapshots=[], fills=[], annualization_basis=252
        )
    }

    assert metrics["final_equity"].status == MetricStatus.NOT_AVAILABLE
    assert metrics["final_equity"].reason == "no_valid_portfolio_snapshots"
    assert metrics["total_return"].status == MetricStatus.NOT_AVAILABLE
    assert metrics["max_drawdown"].status == MetricStatus.NOT_AVAILABLE
    assert metrics["exposure_time_ratio"].status == MetricStatus.NOT_AVAILABLE
    assert metrics["trade_count"].value == Decimal("0")
    assert metrics["win_rate"].status == MetricStatus.NOT_AVAILABLE
    assert metrics["win_rate"].reason == "zero_trades"
