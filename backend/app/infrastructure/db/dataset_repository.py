from typing import Any

from app.domain.dataset import DatasetManifest, DatasetValidationStatus, InstrumentMappingPolicy
from app.domain.pagination import Page
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "dataset_id",
    "version",
    "name",
    "source_name",
    "source_reference",
    "license_reference",
    "content_checksum",
    "bar_interval",
    "timezone",
    "adjustment_policy",
    "coverage_start_date",
    "coverage_end_date",
    "created_at_utc",
    "validation_status",
    "validation_summary",
    "instrument_mapping_policy",
)


def _row_to_dataset(row: dict[str, Any]) -> DatasetManifest:
    return DatasetManifest(
        dataset_id=row["dataset_id"],
        version=row["version"],
        name=row["name"],
        source_name=row["source_name"],
        source_reference=row["source_reference"],
        license_reference=row["license_reference"],
        content_checksum=row["content_checksum"],
        bar_interval=row["bar_interval"],
        timezone=row["timezone"],
        adjustment_policy=row["adjustment_policy"],
        coverage_start_date=row["coverage_start_date"],
        coverage_end_date=row["coverage_end_date"],
        created_at_utc=from_naive_utc(row["created_at_utc"]),
        validation_status=DatasetValidationStatus(row["validation_status"]),
        validation_summary=row["validation_summary"],
        instrument_mapping_policy=InstrumentMappingPolicy(row["instrument_mapping_policy"]),
    )


class DuckDBDatasetRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, dataset: DatasetManifest) -> DatasetManifest:
        with connect(self._settings) as connection:
            connection.execute(
                f"""
                INSERT INTO datasets ({", ".join(_COLUMNS)})
                VALUES ({", ".join("?" for _ in _COLUMNS)})
                """,
                [
                    dataset.dataset_id,
                    dataset.version,
                    dataset.name,
                    dataset.source_name,
                    dataset.source_reference,
                    dataset.license_reference,
                    dataset.content_checksum,
                    dataset.bar_interval,
                    dataset.timezone,
                    dataset.adjustment_policy,
                    dataset.coverage_start_date,
                    dataset.coverage_end_date,
                    to_naive_utc(dataset.created_at_utc),
                    dataset.validation_status.value,
                    dataset.validation_summary,
                    dataset.instrument_mapping_policy.value,
                ],
            )
        return dataset

    def get(self, dataset_id: str) -> DatasetManifest | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM datasets WHERE dataset_id = ?", [dataset_id]
            ).fetchone()
        if row is None:
            return None
        return _row_to_dataset(dict(zip(_COLUMNS, row, strict=True)))

    def list(self, *, limit: int, offset: int) -> Page[DatasetManifest]:
        with connect(self._settings) as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM datasets
                ORDER BY created_at_utc, dataset_id
                LIMIT ? OFFSET ?
                """,
                [limit, offset],
            ).fetchall()
        items = [_row_to_dataset(dict(zip(_COLUMNS, row, strict=True))) for row in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)
