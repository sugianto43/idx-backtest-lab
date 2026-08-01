from typing import Any

from app.domain.market_data import DatasetValidationEvent, ValidationSeverity
from app.domain.pagination import Page
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "event_id",
    "import_id",
    "dataset_id",
    "severity",
    "code",
    "message",
    "source_row_number",
    "created_at_utc",
)


def _row_to_event(row: dict[str, Any]) -> DatasetValidationEvent:
    return DatasetValidationEvent(
        event_id=row["event_id"],
        import_id=row["import_id"],
        dataset_id=row["dataset_id"],
        severity=ValidationSeverity(row["severity"]),
        code=row["code"],
        message=row["message"],
        source_row_number=row["source_row_number"],
        created_at_utc=from_naive_utc(row["created_at_utc"]),
    )


class DuckDBDatasetValidationEventRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def list_for_dataset(
        self, dataset_id: str, *, limit: int, offset: int
    ) -> Page[DatasetValidationEvent]:
        with connect(self._settings) as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM dataset_validation_events WHERE dataset_id = ?",
                    [dataset_id],
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM dataset_validation_events
                WHERE dataset_id = ?
                ORDER BY created_at_utc, event_id
                LIMIT ? OFFSET ?
                """,
                [dataset_id, limit, offset],
            ).fetchall()
        items = [_row_to_event(dict(zip(_COLUMNS, row, strict=True))) for row in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)
