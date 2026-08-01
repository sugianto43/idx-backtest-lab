from typing import Any

from app.domain.dataset import DatasetValidationStatus
from app.domain.market_data import DatasetImport
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "import_id",
    "dataset_id",
    "raw_filename",
    "content_checksum",
    "byte_size",
    "requested_metadata",
    "status",
    "row_count",
    "accepted_row_count",
    "warning_count",
    "error_count",
    "started_at_utc",
    "finished_at_utc",
    "failure_code",
    "failure_row_number",
)


def _row_to_import(row: dict[str, Any]) -> DatasetImport:
    return DatasetImport(
        import_id=row["import_id"],
        dataset_id=row["dataset_id"],
        raw_filename=row["raw_filename"],
        content_checksum=row["content_checksum"],
        byte_size=row["byte_size"],
        requested_metadata_json=row["requested_metadata"],
        status=DatasetValidationStatus(row["status"]),
        row_count=row["row_count"],
        accepted_row_count=row["accepted_row_count"],
        warning_count=row["warning_count"],
        error_count=row["error_count"],
        started_at_utc=from_naive_utc(row["started_at_utc"]),
        finished_at_utc=from_naive_utc(row["finished_at_utc"]),
        failure_code=row["failure_code"],
        failure_row_number=row["failure_row_number"],
    )


class DuckDBDatasetImportRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get(self, import_id: str) -> DatasetImport | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM dataset_imports WHERE import_id = ?",
                [import_id],
            ).fetchone()
        if row is None:
            return None
        return _row_to_import(dict(zip(_COLUMNS, row, strict=True)))

    def find_by_content_checksum(self, content_checksum: str) -> DatasetImport | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM dataset_imports
                WHERE content_checksum = ? AND status IN ('valid', 'warning')
                ORDER BY started_at_utc DESC
                LIMIT 1
                """,
                [content_checksum],
            ).fetchone()
        if row is None:
            return None
        return _row_to_import(dict(zip(_COLUMNS, row, strict=True)))

    def get_latest_for_dataset(self, dataset_id: str) -> DatasetImport | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM dataset_imports
                WHERE dataset_id = ?
                ORDER BY started_at_utc DESC
                LIMIT 1
                """,
                [dataset_id],
            ).fetchone()
        if row is None:
            return None
        return _row_to_import(dict(zip(_COLUMNS, row, strict=True)))
