from typing import Any

from app.domain.corporate_action import CorporateAction, CorporateActionStatus, CorporateActionType
from app.domain.pagination import Page
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "event_id",
    "instrument_id",
    "event_type",
    "effective_date",
    "announcement_date",
    "status",
    "source_name",
    "source_reference",
    "payload_json",
    "supersedes_event_id",
    "created_at_utc",
)


def _row_to_action(row: dict[str, Any]) -> CorporateAction:
    return CorporateAction(
        event_id=row["event_id"],
        instrument_id=row["instrument_id"],
        event_type=CorporateActionType(row["event_type"]),
        effective_date=row["effective_date"],
        announcement_date=row["announcement_date"],
        status=CorporateActionStatus(row["status"]),
        source_name=row["source_name"],
        source_reference=row["source_reference"],
        payload_json=row["payload_json"],
        supersedes_event_id=row["supersedes_event_id"],
        created_at_utc=from_naive_utc(row["created_at_utc"]),
    )


class DuckDBCorporateActionRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, action: CorporateAction) -> CorporateAction:
        with connect(self._settings) as connection:
            connection.execute(
                f"""
                INSERT INTO corporate_actions ({", ".join(_COLUMNS)})
                VALUES ({", ".join("?" for _ in _COLUMNS)})
                """,
                [
                    action.event_id,
                    action.instrument_id,
                    action.event_type.value,
                    action.effective_date,
                    action.announcement_date,
                    action.status.value,
                    action.source_name,
                    action.source_reference,
                    action.payload_json,
                    action.supersedes_event_id,
                    to_naive_utc(action.created_at_utc),
                ],
            )
        return action

    def get(self, event_id: str) -> CorporateAction | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM corporate_actions WHERE event_id = ?",
                [event_id],
            ).fetchone()
        if row is None:
            return None
        return _row_to_action(dict(zip(_COLUMNS, row, strict=True)))

    def list_for_instrument(
        self, instrument_id: str, *, limit: int, offset: int
    ) -> Page[CorporateAction]:
        with connect(self._settings) as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM corporate_actions WHERE instrument_id = ?",
                    [instrument_id],
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM corporate_actions
                WHERE instrument_id = ?
                ORDER BY effective_date, event_id
                LIMIT ? OFFSET ?
                """,
                [instrument_id, limit, offset],
            ).fetchall()
        items = [_row_to_action(dict(zip(_COLUMNS, row, strict=True))) for row in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)
