import uuid
from typing import Any

from app.domain.execution_result import (
    CashEvent,
    ExecutionWarning,
    FillEvent,
    OrderEvent,
    PositionEvent,
)
from app.domain.run_artifact import (
    MetricRecord,
    PortfolioSnapshot,
    ReproducibilityManifest,
    RunArtifactBundle,
)
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import to_naive_utc
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
    "bundle_id",
    "run_id",
    "sequence",
    "instrument_id",
    "side",
    "created_at_utc",
    "intended_quantity",
    "status",
    "rejection_reason",
)
_FILL_COLUMNS = (
    "fill_id",
    "bundle_id",
    "run_id",
    "sequence",
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
_POSITION_COLUMNS = (
    "position_event_id",
    "bundle_id",
    "run_id",
    "sequence",
    "timestamp_utc",
    "instrument_id",
    "quantity",
    "average_cost",
    "reason",
)
_CASH_COLUMNS = (
    "cash_event_id",
    "bundle_id",
    "run_id",
    "sequence",
    "timestamp_utc",
    "currency",
    "cash_before",
    "cash_after",
    "reason",
)
_WARNING_COLUMNS = (
    "warning_id",
    "bundle_id",
    "run_id",
    "sequence",
    "code",
    "message",
    "instrument_id",
    "timestamp_utc",
)
_SNAPSHOT_COLUMNS = (
    "snapshot_id",
    "bundle_id",
    "run_id",
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
    "metric_id",
    "bundle_id",
    "run_id",
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


def _insert(connection: Any, table: str, columns: tuple[str, ...], rows: list[list[Any]]) -> None:
    if not rows:
        return
    connection.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
        rows,
    )


class DuckDBRunArtifactWriter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def persist(
        self,
        *,
        bundle: RunArtifactBundle,
        order_events: list[OrderEvent],
        fill_events: list[FillEvent],
        position_events: list[PositionEvent],
        cash_events: list[CashEvent],
        warnings: list[ExecutionWarning],
        snapshots: list[PortfolioSnapshot],
        metrics: list[MetricRecord],
        reproducibility_manifest: ReproducibilityManifest,
    ) -> None:
        with connect(self._settings) as connection:
            try:
                connection.execute("BEGIN TRANSACTION")
                connection.execute(
                    f"INSERT INTO run_artifact_bundles ({', '.join(_BUNDLE_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in _BUNDLE_COLUMNS)})",
                    [
                        bundle.bundle_id,
                        bundle.run_id,
                        bundle.artifact_schema_version,
                        bundle.checksum,
                        bundle.terminal_status,
                        bundle.provenance_json,
                        bundle.event_count,
                        bundle.snapshot_count,
                        bundle.metric_count,
                        to_naive_utc(bundle.created_at_utc),
                    ],
                )

                _insert(
                    connection,
                    "run_order_events",
                    _ORDER_COLUMNS,
                    [
                        [
                            event.order_id,
                            bundle.bundle_id,
                            bundle.run_id,
                            sequence,
                            event.instrument_id,
                            event.side.value,
                            to_naive_utc(event.created_at_utc),
                            event.intended_quantity,
                            event.status.value,
                            event.rejection_reason,
                        ]
                        for sequence, event in enumerate(order_events)
                    ],
                )
                _insert(
                    connection,
                    "run_fill_events",
                    _FILL_COLUMNS,
                    [
                        [
                            uuid.uuid4().hex,
                            bundle.bundle_id,
                            bundle.run_id,
                            sequence,
                            event.order_id,
                            event.instrument_id,
                            event.side.value,
                            to_naive_utc(event.filled_at_utc),
                            event.quantity,
                            event.price,
                            event.currency,
                            event.commission,
                            event.tax,
                            event.slippage,
                        ]
                        for sequence, event in enumerate(fill_events)
                    ],
                )
                _insert(
                    connection,
                    "run_position_events",
                    _POSITION_COLUMNS,
                    [
                        [
                            uuid.uuid4().hex,
                            bundle.bundle_id,
                            bundle.run_id,
                            sequence,
                            to_naive_utc(event.timestamp_utc),
                            event.instrument_id,
                            event.quantity,
                            event.average_cost,
                            event.reason,
                        ]
                        for sequence, event in enumerate(position_events)
                    ],
                )
                _insert(
                    connection,
                    "run_cash_events",
                    _CASH_COLUMNS,
                    [
                        [
                            uuid.uuid4().hex,
                            bundle.bundle_id,
                            bundle.run_id,
                            sequence,
                            to_naive_utc(event.timestamp_utc),
                            event.currency,
                            event.cash_before,
                            event.cash_after,
                            event.reason,
                        ]
                        for sequence, event in enumerate(cash_events)
                    ],
                )
                _insert(
                    connection,
                    "run_warnings",
                    _WARNING_COLUMNS,
                    [
                        [
                            uuid.uuid4().hex,
                            bundle.bundle_id,
                            bundle.run_id,
                            sequence,
                            warning.code,
                            warning.message,
                            warning.instrument_id,
                            to_naive_utc(warning.timestamp_utc) if warning.timestamp_utc else None,
                        ]
                        for sequence, warning in enumerate(warnings)
                    ],
                )
                _insert(
                    connection,
                    "portfolio_snapshots",
                    _SNAPSHOT_COLUMNS,
                    [
                        [
                            uuid.uuid4().hex,
                            bundle.bundle_id,
                            bundle.run_id,
                            snapshot.sequence,
                            to_naive_utc(snapshot.timestamp_utc),
                            snapshot.cash,
                            snapshot.holdings_value,
                            snapshot.total_equity,
                            snapshot.currency,
                            snapshot.status.value,
                            snapshot.reason,
                        ]
                        for snapshot in snapshots
                    ],
                )
                _insert(
                    connection,
                    "run_metrics",
                    _METRIC_COLUMNS,
                    [
                        [
                            uuid.uuid4().hex,
                            bundle.bundle_id,
                            bundle.run_id,
                            metric.metric_key,
                            str(metric.value) if metric.value is not None else None,
                            metric.status.value,
                            metric.reason,
                            metric.definition_version,
                            metric.calculation_input_json,
                        ]
                        for metric in metrics
                    ],
                )
                connection.execute(
                    f"INSERT INTO reproducibility_manifests ({', '.join(_REPRO_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in _REPRO_COLUMNS)})",
                    [
                        reproducibility_manifest.manifest_id,
                        reproducibility_manifest.bundle_id,
                        reproducibility_manifest.run_id,
                        reproducibility_manifest.canonical_json,
                        reproducibility_manifest.checksum,
                        to_naive_utc(reproducibility_manifest.created_at_utc),
                    ],
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
