from datetime import date
from typing import Any

from app.application.errors import UnresolvedInstrumentMappingError
from app.domain.market_data import NormalizedBar
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc
from app.infrastructure.settings import Settings

_BAR_COLUMNS = (
    "bar_id",
    "dataset_id",
    "source_instrument_identifier",
    "timestamp_utc",
    "bar_interval",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "currency",
    "source_row_id",
)


def _row_to_bar(row: dict[str, Any]) -> NormalizedBar:
    return NormalizedBar(
        bar_id=row["bar_id"],
        dataset_id=row["dataset_id"],
        source_instrument_identifier=row["source_instrument_identifier"],
        timestamp_utc=from_naive_utc(row["timestamp_utc"]),
        bar_interval=row["bar_interval"],
        open=row["open"],
        high=row["high"],
        low=row["low"],
        close=row["close"],
        volume=row["volume"],
        currency=row["currency"],
        source_row_id=row["source_row_id"],
    )


class DuckDBBarSnapshotRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_snapshot(
        self, *, dataset_id: str, instrument_id: str, start_date: date, end_date: date
    ) -> list[NormalizedBar]:
        with connect(self._settings) as connection:
            mapping_row = connection.execute(
                """
                SELECT source_instrument_identifier FROM dataset_instrument_mappings
                WHERE dataset_id = ? AND instrument_id = ?
                  AND effective_from <= ?
                  AND (effective_to IS NULL OR effective_to >= ?)
                ORDER BY effective_from
                LIMIT 1
                """,
                [dataset_id, instrument_id, end_date, start_date],
            ).fetchone()
            if mapping_row is None:
                raise UnresolvedInstrumentMappingError(dataset_id, instrument_id)
            source_instrument_identifier = mapping_row[0]

            rows = connection.execute(
                f"""
                SELECT {", ".join(_BAR_COLUMNS)} FROM normalized_bars
                WHERE dataset_id = ? AND source_instrument_identifier = ?
                  AND timestamp_utc >= ? AND timestamp_utc < ?
                ORDER BY timestamp_utc
                """,
                [
                    dataset_id,
                    source_instrument_identifier,
                    start_date,
                    date.fromordinal(end_date.toordinal() + 1),
                ],
            ).fetchall()
        return [_row_to_bar(dict(zip(_BAR_COLUMNS, row, strict=True))) for row in rows]
