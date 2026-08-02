import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.execution_result import CashEvent, FillEvent, OrderSide, PositionEvent
from app.domain.market_data import NormalizedBar

ARTIFACT_SCHEMA_VERSION = 1
METRIC_DEFINITION_VERSION = 1


class SnapshotValuationStatus(StrEnum):
    VALID = "valid"
    NOT_AVAILABLE = "not_available"


class MetricStatus(StrEnum):
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    sequence: int
    timestamp_utc: datetime
    cash: Decimal
    holdings_value: Decimal
    total_equity: Decimal
    currency: str
    status: SnapshotValuationStatus
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class MetricRecord:
    metric_key: str
    status: MetricStatus
    definition_version: int
    calculation_input_json: str
    value: Decimal | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RunArtifactBundle:
    bundle_id: str
    run_id: str
    artifact_schema_version: int
    checksum: str
    terminal_status: str
    provenance_json: str
    event_count: int
    snapshot_count: int
    metric_count: int
    created_at_utc: datetime


@dataclass(frozen=True, slots=True)
class ReproducibilityManifest:
    manifest_id: str
    bundle_id: str
    run_id: str
    canonical_json: str
    checksum: str
    created_at_utc: datetime


def build_portfolio_snapshots(
    bars: list[NormalizedBar],
    cash_events: tuple[CashEvent, ...],
    position_events: tuple[PositionEvent, ...],
    *,
    initial_cash: Decimal,
    currency: str,
) -> list[PortfolioSnapshot]:
    """Value cash + holdings at each declared bar's close (v1 valuation policy).

    Cash/position events apply from the bar whose timestamp they occur on,
    onward -- fills happen at a bar's open, so the resulting cash/position
    change is visible in that same bar's end-of-bar snapshot.
    """
    cash = initial_cash
    quantity = 0
    cash_idx = 0
    position_idx = 0
    snapshots: list[PortfolioSnapshot] = []

    for sequence, bar in enumerate(bars):
        while (
            cash_idx < len(cash_events) and cash_events[cash_idx].timestamp_utc <= bar.timestamp_utc
        ):
            cash = cash_events[cash_idx].cash_after
            cash_idx += 1
        while (
            position_idx < len(position_events)
            and position_events[position_idx].timestamp_utc <= bar.timestamp_utc
        ):
            quantity = position_events[position_idx].quantity
            position_idx += 1

        holdings_value = (Decimal(quantity) * bar.close) if quantity else Decimal("0")
        total_equity = cash + holdings_value
        snapshots.append(
            PortfolioSnapshot(
                sequence=sequence,
                timestamp_utc=bar.timestamp_utc,
                cash=cash,
                holdings_value=holdings_value,
                total_equity=total_equity,
                currency=currency,
                status=SnapshotValuationStatus.VALID,
            )
        )
    return snapshots


def compute_fifo_realized_pnl(fills: list[FillEvent]) -> list[Decimal]:
    """Realized P&L per completed long-only FIFO round-trip trade.

    v1 is long-only and single-instrument: BUY fills open/add to a FIFO lot
    queue; SELL fills close against the oldest open lot(s) first. A trade is
    "completed" when a SELL fill fully or partially closes open quantity.
    """
    open_lots: list[list[Decimal]] = []  # [quantity, price] pairs, oldest first
    realized: list[Decimal] = []

    for fill in fills:
        if fill.side == OrderSide.BUY:
            open_lots.append([Decimal(fill.quantity), fill.price])
            continue

        remaining = Decimal(fill.quantity)
        pnl = Decimal("0")
        while remaining > 0 and open_lots:
            lot_quantity, lot_price = open_lots[0]
            matched = min(remaining, lot_quantity)
            pnl += matched * (fill.price - lot_price)
            remaining -= matched
            if matched == lot_quantity:
                open_lots.pop(0)
            else:
                open_lots[0][0] = lot_quantity - matched
        pnl -= fill.commission + fill.tax + fill.slippage
        realized.append(pnl)

    return realized


def _not_available(metric_key: str, reason: str) -> MetricRecord:
    return MetricRecord(
        metric_key=metric_key,
        status=MetricStatus.NOT_AVAILABLE,
        reason=reason,
        definition_version=METRIC_DEFINITION_VERSION,
        calculation_input_json="{}",
    )


def _available(
    metric_key: str, value: Decimal, calculation_input: dict[str, object]
) -> MetricRecord:
    return MetricRecord(
        metric_key=metric_key,
        status=MetricStatus.AVAILABLE,
        value=value,
        definition_version=METRIC_DEFINITION_VERSION,
        calculation_input_json=json.dumps(calculation_input, default=str, sort_keys=True),
    )


def _equity_metrics(
    initial_equity: Decimal, valid_snapshots: list[PortfolioSnapshot], annualization_basis: int
) -> list[MetricRecord]:
    final_equity = valid_snapshots[-1].total_equity if valid_snapshots else None
    records = [
        _available("initial_equity", initial_equity, {"capital_amount": str(initial_equity)})
    ]

    if final_equity is None:
        records.append(_not_available("final_equity", "no_valid_portfolio_snapshots"))
        records.append(_not_available("total_return", "missing_equity_endpoint"))
        records.append(_not_available("annualized_return", "insufficient_elapsed_sessions"))
        return records

    records.append(
        _available(
            "final_equity", final_equity, {"snapshot_sequence": valid_snapshots[-1].sequence}
        )
    )

    if initial_equity <= 0:
        records.append(_not_available("total_return", "missing_equity_endpoint"))
        records.append(_not_available("annualized_return", "insufficient_elapsed_sessions"))
        return records

    ratio = final_equity / initial_equity
    records.append(
        _available(
            "total_return",
            ratio - 1,
            {"initial_equity": str(initial_equity), "final_equity": str(final_equity)},
        )
    )

    elapsed_sessions = len(valid_snapshots) - 1
    if elapsed_sessions > 0:
        annualized = ratio ** (Decimal(annualization_basis) / Decimal(elapsed_sessions)) - 1
        records.append(
            _available(
                "annualized_return",
                annualized,
                {
                    "annualization_basis": annualization_basis,
                    "elapsed_session_count": elapsed_sessions,
                },
            )
        )
    else:
        records.append(_not_available("annualized_return", "insufficient_elapsed_sessions"))

    return records


def _max_drawdown_metric(valid_snapshots: list[PortfolioSnapshot]) -> MetricRecord:
    if not valid_snapshots:
        return _not_available("max_drawdown", "no_valid_portfolio_snapshots")

    running_max = valid_snapshots[0].total_equity
    min_drawdown = Decimal("0")
    for snapshot in valid_snapshots:
        running_max = max(running_max, snapshot.total_equity)
        if running_max > 0:
            min_drawdown = min(min_drawdown, (snapshot.total_equity / running_max) - 1)
    return _available("max_drawdown", min_drawdown, {"valid_snapshot_count": len(valid_snapshots)})


def _trade_metrics(fills: list[FillEvent]) -> list[MetricRecord]:
    realized_trades = compute_fifo_realized_pnl(fills)
    trade_count = len(realized_trades)
    records = [_available("trade_count", Decimal(trade_count), {"fill_count": len(fills)})]

    if trade_count > 0:
        wins = sum(1 for pnl in realized_trades if pnl > 0)
        records.append(
            _available(
                "win_rate",
                Decimal(wins) / Decimal(trade_count),
                {"trade_count": trade_count, "wins": wins},
            )
        )
    else:
        records.append(_not_available("win_rate", "zero_trades"))

    realized_pnl_sum = sum(realized_trades, Decimal("0"))
    records.append(_available("realized_pnl", realized_pnl_sum, {"trade_count": trade_count}))
    return records


def _exposure_metric(valid_snapshots: list[PortfolioSnapshot]) -> MetricRecord:
    if not valid_snapshots:
        return _not_available("exposure_time_ratio", "no_valid_portfolio_snapshots")

    exposed_sessions = sum(1 for s in valid_snapshots if s.holdings_value > 0)
    ratio = Decimal(exposed_sessions) / Decimal(len(valid_snapshots))
    return _available(
        "exposure_time_ratio",
        ratio,
        {"exposed_sessions": exposed_sessions, "valid_session_count": len(valid_snapshots)},
    )


def compute_metrics(
    *,
    initial_equity: Decimal,
    snapshots: list[PortfolioSnapshot],
    fills: list[FillEvent],
    annualization_basis: int,
) -> list[MetricRecord]:
    valid_snapshots = [s for s in snapshots if s.status == SnapshotValuationStatus.VALID]

    records = _equity_metrics(initial_equity, valid_snapshots, annualization_basis)
    records.append(_max_drawdown_metric(valid_snapshots))
    records.extend(_trade_metrics(fills))
    records.append(_exposure_metric(valid_snapshots))
    return records
