from decimal import Decimal
from typing import Any

from app.domain.execution_result import (
    CashEvent,
    ExecutionWarning,
    FillEvent,
    OrderEvent,
    OrderSide,
    OrderStatus,
    PositionEvent,
)
from app.domain.pagination import Page
from app.domain.run_artifact import (
    MetricRecord,
    MetricStatus,
    PortfolioSnapshot,
    ReproducibilityManifest,
    RunArtifactBundle,
    SnapshotValuationStatus,
)
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc
from app.infrastructure.settings import Settings

_BUNDLE_COLUMNS = (
    "bundle_id",
    "run_id",
    "artifact_schema_version",
    "checksum",
    "terminal_status",
    "provenance_json",
    "event_count",
    "snapshot_count",
    "metric_count",
    "created_at_utc",
)
_ORDER_COLUMNS = (
    "event_id",
    "instrument_id",
    "side",
    "created_at_utc",
    "intended_quantity",
    "status",
    "rejection_reason",
)
_FILL_COLUMNS = (
    "order_id",
    "instrument_id",
    "side",
    "filled_at_utc",
    "quantity",
    "price",
    "currency",
    "commission",
    "tax",
    "slippage",
)
_POSITION_COLUMNS = ("timestamp_utc", "instrument_id", "quantity", "average_cost", "reason")
_CASH_COLUMNS = ("timestamp_utc", "currency", "cash_before", "cash_after", "reason")
_WARNING_COLUMNS = ("code", "message", "instrument_id", "timestamp_utc")
_SNAPSHOT_COLUMNS = (
    "sequence",
    "timestamp_utc",
    "cash",
    "holdings_value",
    "total_equity",
    "currency",
    "valuation_status",
    "valuation_reason",
)
_METRIC_COLUMNS = (
    "metric_key",
    "value",
    "status",
    "reason",
    "definition_version",
    "calculation_input_json",
)
_REPRO_COLUMNS = (
    "manifest_id",
    "bundle_id",
    "run_id",
    "canonical_json",
    "checksum",
    "created_at_utc",
)


def _row_to_bundle(row: dict[str, Any]) -> RunArtifactBundle:
    return RunArtifactBundle(
        bundle_id=row["bundle_id"],
        run_id=row["run_id"],
        artifact_schema_version=row["artifact_schema_version"],
        checksum=row["checksum"],
        terminal_status=row["terminal_status"],
        provenance_json=row["provenance_json"],
        event_count=row["event_count"],
        snapshot_count=row["snapshot_count"],
        metric_count=row["metric_count"],
        created_at_utc=from_naive_utc(row["created_at_utc"]),
    )


def _row_to_order(row: dict[str, Any]) -> OrderEvent:
    return OrderEvent(
        order_id=row["event_id"],
        instrument_id=row["instrument_id"],
        side=OrderSide(row["side"]),
        created_at_utc=from_naive_utc(row["created_at_utc"]),
        intended_quantity=row["intended_quantity"],
        status=OrderStatus(row["status"]),
        rejection_reason=row["rejection_reason"],
    )


def _row_to_fill(row: dict[str, Any]) -> FillEvent:
    return FillEvent(
        order_id=row["order_id"],
        instrument_id=row["instrument_id"],
        side=OrderSide(row["side"]),
        filled_at_utc=from_naive_utc(row["filled_at_utc"]),
        quantity=row["quantity"],
        price=row["price"],
        currency=row["currency"],
        commission=row["commission"],
        tax=row["tax"],
        slippage=row["slippage"],
    )


def _row_to_position(row: dict[str, Any]) -> PositionEvent:
    return PositionEvent(
        timestamp_utc=from_naive_utc(row["timestamp_utc"]),
        instrument_id=row["instrument_id"],
        quantity=row["quantity"],
        average_cost=row["average_cost"],
        reason=row["reason"],
    )


def _row_to_cash(row: dict[str, Any]) -> CashEvent:
    return CashEvent(
        timestamp_utc=from_naive_utc(row["timestamp_utc"]),
        currency=row["currency"],
        cash_before=row["cash_before"],
        cash_after=row["cash_after"],
        reason=row["reason"],
    )


def _row_to_warning(row: dict[str, Any]) -> ExecutionWarning:
    return ExecutionWarning(
        code=row["code"],
        message=row["message"],
        instrument_id=row["instrument_id"],
        timestamp_utc=from_naive_utc(row["timestamp_utc"]) if row["timestamp_utc"] else None,
    )


def _row_to_snapshot(row: dict[str, Any]) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        sequence=row["sequence"],
        timestamp_utc=from_naive_utc(row["timestamp_utc"]),
        cash=row["cash"],
        holdings_value=row["holdings_value"],
        total_equity=row["total_equity"],
        currency=row["currency"],
        status=SnapshotValuationStatus(row["valuation_status"]),
        reason=row["valuation_reason"],
    )


def _row_to_metric(row: dict[str, Any]) -> MetricRecord:
    return MetricRecord(
        metric_key=row["metric_key"],
        value=Decimal(row["value"]) if row["value"] is not None else None,
        status=MetricStatus(row["status"]),
        reason=row["reason"],
        definition_version=row["definition_version"],
        calculation_input_json=row["calculation_input_json"],
    )


def _row_to_repro(row: dict[str, Any]) -> ReproducibilityManifest:
    return ReproducibilityManifest(
        manifest_id=row["manifest_id"],
        bundle_id=row["bundle_id"],
        run_id=row["run_id"],
        canonical_json=row["canonical_json"],
        checksum=row["checksum"],
        created_at_utc=from_naive_utc(row["created_at_utc"]),
    )


class DuckDBRunArtifactRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_bundle(self, run_id: str) -> RunArtifactBundle | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_BUNDLE_COLUMNS)} FROM run_artifact_bundles WHERE run_id = ?",
                [run_id],
            ).fetchone()
        if row is None:
            return None
        return _row_to_bundle(dict(zip(_BUNDLE_COLUMNS, row, strict=True)))

    def _paginate(
        self, table: str, columns: tuple[str, ...], run_id: str, *, limit: int, offset: int
    ) -> tuple[int, list[dict[str, Any]]]:
        with connect(self._settings) as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE run_id = ?", [run_id]
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"""
                SELECT {", ".join(columns)} FROM {table}
                WHERE run_id = ?
                ORDER BY sequence
                LIMIT ? OFFSET ?
                """,
                [run_id, limit, offset],
            ).fetchall()
        return total, [dict(zip(columns, row, strict=True)) for row in rows]

    def list_order_events(self, run_id: str, *, limit: int, offset: int) -> Page[OrderEvent]:
        total, rows = self._paginate(
            "run_order_events", _ORDER_COLUMNS, run_id, limit=limit, offset=offset
        )
        return Page(items=[_row_to_order(r) for r in rows], total=total, limit=limit, offset=offset)

    def list_fill_events(self, run_id: str, *, limit: int, offset: int) -> Page[FillEvent]:
        total, rows = self._paginate(
            "run_fill_events", _FILL_COLUMNS, run_id, limit=limit, offset=offset
        )
        return Page(items=[_row_to_fill(r) for r in rows], total=total, limit=limit, offset=offset)

    def list_position_events(self, run_id: str, *, limit: int, offset: int) -> Page[PositionEvent]:
        total, rows = self._paginate(
            "run_position_events", _POSITION_COLUMNS, run_id, limit=limit, offset=offset
        )
        return Page(
            items=[_row_to_position(r) for r in rows], total=total, limit=limit, offset=offset
        )

    def list_cash_events(self, run_id: str, *, limit: int, offset: int) -> Page[CashEvent]:
        total, rows = self._paginate(
            "run_cash_events", _CASH_COLUMNS, run_id, limit=limit, offset=offset
        )
        return Page(items=[_row_to_cash(r) for r in rows], total=total, limit=limit, offset=offset)

    def list_warnings(self, run_id: str, *, limit: int, offset: int) -> Page[ExecutionWarning]:
        total, rows = self._paginate(
            "run_warnings", _WARNING_COLUMNS, run_id, limit=limit, offset=offset
        )
        return Page(
            items=[_row_to_warning(r) for r in rows], total=total, limit=limit, offset=offset
        )

    def list_portfolio_snapshots(
        self, run_id: str, *, limit: int, offset: int
    ) -> Page[PortfolioSnapshot]:
        total, rows = self._paginate(
            "portfolio_snapshots", _SNAPSHOT_COLUMNS, run_id, limit=limit, offset=offset
        )
        return Page(
            items=[_row_to_snapshot(r) for r in rows], total=total, limit=limit, offset=offset
        )

    def list_metrics(self, run_id: str) -> list[MetricRecord]:
        with connect(self._settings) as connection:
            rows = connection.execute(
                f"SELECT {', '.join(_METRIC_COLUMNS)} FROM run_metrics "
                "WHERE run_id = ? ORDER BY metric_key",
                [run_id],
            ).fetchall()
        return [_row_to_metric(dict(zip(_METRIC_COLUMNS, row, strict=True))) for row in rows]

    def get_reproducibility_manifest(self, run_id: str) -> ReproducibilityManifest | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_REPRO_COLUMNS)} FROM reproducibility_manifests "
                "WHERE run_id = ?",
                [run_id],
            ).fetchone()
        if row is None:
            return None
        return _row_to_repro(dict(zip(_REPRO_COLUMNS, row, strict=True)))
