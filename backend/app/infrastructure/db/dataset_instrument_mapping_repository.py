from datetime import date
from typing import Any

from app.domain.date_ranges import date_ranges_overlap
from app.domain.instrument import DatasetInstrumentMapping, MappingStatus
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "mapping_id",
    "dataset_id",
    "source_instrument_identifier",
    "instrument_id",
    "effective_from",
    "effective_to",
    "decision_source",
    "status",
    "created_at_utc",
)


def _row_to_mapping(row: dict[str, Any]) -> DatasetInstrumentMapping:
    return DatasetInstrumentMapping(
        mapping_id=row["mapping_id"],
        dataset_id=row["dataset_id"],
        source_instrument_identifier=row["source_instrument_identifier"],
        instrument_id=row["instrument_id"],
        effective_from=row["effective_from"],
        effective_to=row["effective_to"],
        decision_source=row["decision_source"],
        status=MappingStatus(row["status"]),
        created_at_utc=from_naive_utc(row["created_at_utc"]),
    )


class DuckDBDatasetInstrumentMappingRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, mapping: DatasetInstrumentMapping) -> DatasetInstrumentMapping:
        with connect(self._settings) as connection:
            connection.execute(
                f"""
                INSERT INTO dataset_instrument_mappings ({", ".join(_COLUMNS)})
                VALUES ({", ".join("?" for _ in _COLUMNS)})
                """,
                [
                    mapping.mapping_id,
                    mapping.dataset_id,
                    mapping.source_instrument_identifier,
                    mapping.instrument_id,
                    mapping.effective_from,
                    mapping.effective_to,
                    mapping.decision_source,
                    mapping.status.value,
                    to_naive_utc(mapping.created_at_utc),
                ],
            )
        return mapping

    def list_for_dataset(self, dataset_id: str) -> list[DatasetInstrumentMapping]:
        with connect(self._settings) as connection:
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM dataset_instrument_mappings
                WHERE dataset_id = ?
                ORDER BY effective_from, mapping_id
                """,
                [dataset_id],
            ).fetchall()
        return [_row_to_mapping(dict(zip(_COLUMNS, row, strict=True))) for row in rows]

    def list_for_instrument(self, instrument_id: str) -> list[DatasetInstrumentMapping]:
        with connect(self._settings) as connection:
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM dataset_instrument_mappings
                WHERE instrument_id = ?
                ORDER BY effective_from, mapping_id
                """,
                [instrument_id],
            ).fetchall()
        return [_row_to_mapping(dict(zip(_COLUMNS, row, strict=True))) for row in rows]

    def find_overlapping(
        self,
        *,
        dataset_id: str,
        source_instrument_identifier: str,
        effective_from: date,
        effective_to: date | None,
    ) -> list[DatasetInstrumentMapping]:
        with connect(self._settings) as connection:
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM dataset_instrument_mappings
                WHERE dataset_id = ? AND source_instrument_identifier = ?
                """,
                [dataset_id, source_instrument_identifier],
            ).fetchall()
        candidates = [_row_to_mapping(dict(zip(_COLUMNS, row, strict=True))) for row in rows]
        return [
            candidate
            for candidate in candidates
            if date_ranges_overlap(
                effective_from, effective_to, candidate.effective_from, candidate.effective_to
            )
        ]
