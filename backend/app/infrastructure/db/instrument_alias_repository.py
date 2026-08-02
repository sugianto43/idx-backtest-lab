from datetime import date
from typing import Any

from app.domain.date_ranges import date_ranges_overlap
from app.domain.instrument import AliasConfidence, InstrumentAlias
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "alias_id",
    "instrument_id",
    "symbol",
    "exchange_code",
    "effective_from",
    "effective_to",
    "source_name",
    "source_reference",
    "confidence",
    "created_at_utc",
)


def _row_to_alias(row: dict[str, Any]) -> InstrumentAlias:
    return InstrumentAlias(
        alias_id=row["alias_id"],
        instrument_id=row["instrument_id"],
        symbol=row["symbol"],
        exchange_code=row["exchange_code"],
        effective_from=row["effective_from"],
        effective_to=row["effective_to"],
        source_name=row["source_name"],
        source_reference=row["source_reference"],
        confidence=AliasConfidence(row["confidence"]),
        created_at_utc=from_naive_utc(row["created_at_utc"]),
    )


class DuckDBInstrumentAliasRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, alias: InstrumentAlias) -> InstrumentAlias:
        with connect(self._settings) as connection:
            connection.execute(
                f"""
                INSERT INTO instrument_aliases ({", ".join(_COLUMNS)})
                VALUES ({", ".join("?" for _ in _COLUMNS)})
                """,
                [
                    alias.alias_id,
                    alias.instrument_id,
                    alias.symbol,
                    alias.exchange_code,
                    alias.effective_from,
                    alias.effective_to,
                    alias.source_name,
                    alias.source_reference,
                    alias.confidence.value,
                    to_naive_utc(alias.created_at_utc),
                ],
            )
        return alias

    def list_for_instrument(self, instrument_id: str) -> list[InstrumentAlias]:
        with connect(self._settings) as connection:
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM instrument_aliases
                WHERE instrument_id = ?
                ORDER BY effective_from, alias_id
                """,
                [instrument_id],
            ).fetchall()
        return [_row_to_alias(dict(zip(_COLUMNS, row, strict=True))) for row in rows]

    def find_overlapping(
        self,
        *,
        symbol: str,
        exchange_code: str,
        effective_from: date,
        effective_to: date | None,
    ) -> list[InstrumentAlias]:
        with connect(self._settings) as connection:
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM instrument_aliases
                WHERE symbol = ? AND exchange_code = ?
                """,
                [symbol, exchange_code],
            ).fetchall()
        candidates = [_row_to_alias(dict(zip(_COLUMNS, row, strict=True))) for row in rows]
        return [
            candidate
            for candidate in candidates
            if date_ranges_overlap(
                effective_from, effective_to, candidate.effective_from, candidate.effective_to
            )
        ]
