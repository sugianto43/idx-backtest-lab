from typing import Any

from app.domain.instrument import Instrument, InstrumentStatus, InstrumentType
from app.domain.pagination import Page
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "instrument_id",
    "instrument_type",
    "display_name",
    "currency",
    "status",
    "source_name",
    "source_reference",
    "created_at_utc",
)


def _row_to_instrument(row: dict[str, Any]) -> Instrument:
    return Instrument(
        instrument_id=row["instrument_id"],
        instrument_type=InstrumentType(row["instrument_type"]),
        display_name=row["display_name"],
        currency=row["currency"],
        status=InstrumentStatus(row["status"]),
        source_name=row["source_name"],
        source_reference=row["source_reference"],
        created_at_utc=from_naive_utc(row["created_at_utc"]),
    )


class DuckDBInstrumentRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, instrument: Instrument) -> Instrument:
        with connect(self._settings) as connection:
            connection.execute(
                f"""
                INSERT INTO instruments ({", ".join(_COLUMNS)})
                VALUES ({", ".join("?" for _ in _COLUMNS)})
                """,
                [
                    instrument.instrument_id,
                    instrument.instrument_type.value,
                    instrument.display_name,
                    instrument.currency,
                    instrument.status.value,
                    instrument.source_name,
                    instrument.source_reference,
                    to_naive_utc(instrument.created_at_utc),
                ],
            )
        return instrument

    def get(self, instrument_id: str) -> Instrument | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM instruments WHERE instrument_id = ?",
                [instrument_id],
            ).fetchone()
        if row is None:
            return None
        return _row_to_instrument(dict(zip(_COLUMNS, row, strict=True)))

    def list(self, *, limit: int, offset: int) -> Page[Instrument]:
        with connect(self._settings) as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM instruments").fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM instruments
                ORDER BY created_at_utc, instrument_id
                LIMIT ? OFFSET ?
                """,
                [limit, offset],
            ).fetchall()
        items = [_row_to_instrument(dict(zip(_COLUMNS, row, strict=True))) for row in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)
