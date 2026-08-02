import logging
from collections.abc import Callable
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import Any

import backtrader as bt

from app.domain.backtest_manifest import RunManifestV1
from app.domain.execution_result import (
    CashEvent,
    ExecutionMetadata,
    ExecutionResult,
    ExecutionWarning,
    FillEvent,
    OrderEvent,
    OrderSide,
    OrderStatus,
    PositionEvent,
    TerminalStatus,
)
from app.domain.market_data import NormalizedBar
from app.domain.strategy_spec import StrategySpecV1

logger = logging.getLogger(__name__)

ADAPTER_NAME = "backtrader"
ADAPTER_VERSION = "1.9.78.123"
ORDERING_POLICY = "stable_by_instrument_id"


class _ListFeed(bt.feed.DataBase):  # type: ignore[misc]
    params = (("bars", None),)

    def start(self) -> None:
        super().start()
        self._iterator = iter(self.p.bars)

    def _load(self) -> bool:
        try:
            bar = next(self._iterator)
        except StopIteration:
            return False
        self.lines.datetime[0] = bt.date2num(bar.timestamp_utc)
        self.lines.open[0] = float(bar.open)
        self.lines.high[0] = float(bar.high)
        self.lines.low[0] = float(bar.low)
        self.lines.close[0] = float(bar.close)
        self.lines.volume[0] = float(bar.volume)
        self.lines.openinterest[0] = 0.0
        return True


class _SmaCrossoverStrategy(bt.Strategy):  # type: ignore[misc]
    params = (
        ("bars", None),
        ("instrument_id", None),
        ("fast_window", None),
        ("slow_window", None),
        ("eligible_after_bars", None),
        ("fraction", None),
        ("quantity_increment", None),
        ("money_scale", None),
        ("currency", None),
        ("initial_cash", None),
        ("id_factory", None),
    )

    def __init__(self) -> None:
        self.fast_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.fast_window
        )
        self.slow_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.slow_window
        )
        self.cross = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)

        self.available_cash: Decimal = self.p.initial_cash
        self.order_events: list[OrderEvent] = []
        self.fill_events: list[FillEvent] = []
        self.position_events: list[PositionEvent] = []
        self.cash_events: list[CashEvent] = []
        self.warnings: list[ExecutionWarning] = []
        self.failure_code: str | None = None
        self._order_context: dict[int, dict[str, Any]] = {}
        self._quantum = Decimal(1).scaleb(-self.p.money_scale)

    def _bar_at(self, index: int) -> NormalizedBar:
        bar: NormalizedBar = self.p.bars[index]
        return bar

    def next(self) -> None:
        idx = len(self.data) - 1
        if idx + 1 < self.p.eligible_after_bars:
            return

        bar = self._bar_at(idx)

        if self.cross[0] > 0 and self.position.size == 0:
            self._submit_entry(bar)
        elif self.cross[0] < 0 and self.position.size > 0:
            self._submit_exit(bar)

    def _submit_entry(self, bar: NormalizedBar) -> None:
        if bar.close <= 0:
            return
        budget = (self.available_cash * self.p.fraction).quantize(
            self._quantum, rounding=ROUND_DOWN
        )
        raw_units = budget / bar.close / self.p.quantity_increment
        units = raw_units.to_integral_value(rounding=ROUND_DOWN)
        quantity = units * self.p.quantity_increment
        int_quantity = int(quantity)
        if int_quantity <= 0:
            self.warnings.append(
                ExecutionWarning(
                    code="position_sizing_zero_quantity",
                    message=(
                        "Available cash and fraction round down to zero quantity; "
                        "no order submitted."
                    ),
                    instrument_id=self.p.instrument_id,
                    timestamp_utc=bar.timestamp_utc,
                )
            )
            return

        order_id = self.p.id_factory()
        bt_order = self.buy(size=int_quantity)
        self._order_context[bt_order.ref] = {
            "order_id": order_id,
            "side": OrderSide.BUY,
            "intended_quantity": int_quantity,
            "created_at_utc": bar.timestamp_utc,
        }

    def _submit_exit(self, bar: NormalizedBar) -> None:
        quantity = int(self.position.size)
        order_id = self.p.id_factory()
        bt_order = self.close()
        self._order_context[bt_order.ref] = {
            "order_id": order_id,
            "side": OrderSide.SELL,
            "intended_quantity": quantity,
            "created_at_utc": bar.timestamp_utc,
        }

    def notify_order(self, order: Any) -> None:
        context = self._order_context.get(order.ref)
        if context is None:
            return

        if order.status == order.Completed:
            self._handle_fill(order, context)
        elif order.status in (order.Canceled, order.Margin, order.Rejected):
            self.order_events.append(
                OrderEvent(
                    order_id=context["order_id"],
                    instrument_id=self.p.instrument_id,
                    side=context["side"],
                    created_at_utc=context["created_at_utc"],
                    intended_quantity=context["intended_quantity"],
                    status=OrderStatus.REJECTED,
                    rejection_reason=order.getstatusname(),
                )
            )
            del self._order_context[order.ref]

    def _handle_fill(self, order: Any, context: dict[str, Any]) -> None:
        fill_idx = len(self.data) - 1
        fill_bar = self._bar_at(fill_idx)
        fill_price = fill_bar.open
        quantity = context["intended_quantity"]
        side = context["side"]

        self.order_events.append(
            OrderEvent(
                order_id=context["order_id"],
                instrument_id=self.p.instrument_id,
                side=side,
                created_at_utc=context["created_at_utc"],
                intended_quantity=quantity,
                status=OrderStatus.FILLED,
            )
        )

        cash_before = self.available_cash
        trade_value = fill_price * quantity
        if side == OrderSide.BUY:
            self.available_cash -= trade_value
            avg_cost = fill_price
            position_quantity = quantity
            reason = "buy_fill"
        else:
            self.available_cash += trade_value
            avg_cost = Decimal("0")
            position_quantity = 0
            reason = "sell_fill"

        self.fill_events.append(
            FillEvent(
                order_id=context["order_id"],
                instrument_id=self.p.instrument_id,
                side=side,
                filled_at_utc=fill_bar.timestamp_utc,
                quantity=quantity,
                price=fill_price,
                currency=self.p.currency,
                commission=Decimal("0"),
                tax=Decimal("0"),
                slippage=Decimal("0"),
            )
        )
        self.cash_events.append(
            CashEvent(
                timestamp_utc=fill_bar.timestamp_utc,
                currency=self.p.currency,
                cash_before=cash_before,
                cash_after=self.available_cash,
                reason=reason,
            )
        )
        self.position_events.append(
            PositionEvent(
                timestamp_utc=fill_bar.timestamp_utc,
                instrument_id=self.p.instrument_id,
                quantity=position_quantity,
                average_cost=avg_cost,
                reason=reason,
            )
        )
        if fill_bar.volume == 0:
            self.warnings.append(
                ExecutionWarning(
                    code="zero_volume_fill",
                    message="Fill occurred on a bar with zero recorded volume.",
                    instrument_id=self.p.instrument_id,
                    timestamp_utc=fill_bar.timestamp_utc,
                )
            )
        del self._order_context[order.ref]

    def stop(self) -> None:
        if self._order_context:
            self.failure_code = "missing_next_bar"


def _build_metadata(
    manifest_checksum: str,
    dataset_checksum: str,
    started_at: datetime,
    finished_at: datetime,
    event_count: int,
) -> ExecutionMetadata:
    return ExecutionMetadata(
        adapter_name=ADAPTER_NAME,
        adapter_version=ADAPTER_VERSION,
        manifest_checksum=manifest_checksum,
        dataset_checksum=dataset_checksum,
        ordering_policy=ORDERING_POLICY,
        started_at_utc=started_at,
        finished_at_utc=finished_at,
        event_count=event_count,
    )


class BacktraderEngineAdapter:
    def execute(
        self,
        *,
        manifest: RunManifestV1,
        manifest_checksum: str,
        strategy: StrategySpecV1,
        instrument_id: str,
        bars: list[NormalizedBar],
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> ExecutionResult:
        started_at = clock()
        try:
            cerebro = bt.Cerebro(stdstats=False)
            cerebro.broker.setcash(float(manifest.capital.amount))
            cerebro.broker.setcommission(commission=0.0)
            cerebro.adddata(_ListFeed(bars=bars))
            cerebro.addstrategy(
                _SmaCrossoverStrategy,
                bars=bars,
                instrument_id=instrument_id,
                fast_window=strategy.parameters.fast_window,
                slow_window=strategy.parameters.slow_window,
                eligible_after_bars=strategy.signal_policy.eligible_after_bars,
                fraction=manifest.execution.position_sizing.fraction,
                quantity_increment=manifest.execution.rounding.quantity_increment,
                money_scale=manifest.execution.rounding.money_scale,
                currency=manifest.capital.currency,
                initial_cash=manifest.capital.amount,
                id_factory=id_factory,
            )
            strategies = cerebro.run()
        except Exception:
            logger.exception("Backtrader execution failed for run %s", manifest.run_id)
            finished_at = clock()
            return ExecutionResult(
                metadata=_build_metadata(
                    manifest_checksum,
                    manifest.dataset_ref.content_checksum,
                    started_at,
                    finished_at,
                    0,
                ),
                order_events=(),
                fill_events=(),
                position_events=(),
                cash_events=(),
                warnings=(),
                terminal_status=TerminalStatus.FAILED,
                failure_code="engine_error",
            )

        strat = strategies[0]
        finished_at = clock()
        event_count = (
            len(strat.order_events)
            + len(strat.fill_events)
            + len(strat.position_events)
            + len(strat.cash_events)
        )
        metadata = _build_metadata(
            manifest_checksum,
            manifest.dataset_ref.content_checksum,
            started_at,
            finished_at,
            event_count,
        )

        terminal_status = (
            TerminalStatus.FAILED if strat.failure_code is not None else TerminalStatus.COMPLETED
        )

        return ExecutionResult(
            metadata=metadata,
            order_events=tuple(strat.order_events),
            fill_events=tuple(strat.fill_events),
            position_events=tuple(strat.position_events),
            cash_events=tuple(strat.cash_events),
            warnings=tuple(strat.warnings),
            terminal_status=terminal_status,
            failure_code=strat.failure_code,
        )
