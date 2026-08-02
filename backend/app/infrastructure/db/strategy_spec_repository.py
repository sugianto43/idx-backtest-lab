import json
from typing import Any

from app.domain.pagination import Page
from app.domain.strategy_spec import SignalPolicy, StrategySpecV1, build_parameters
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "strategy_id",
    "version",
    "schema_version",
    "name",
    "kind",
    "canonical_json",
    "checksum",
    "created_at_utc",
)


def _row_to_spec(row: dict[str, Any]) -> StrategySpecV1:
    canonical = json.loads(row["canonical_json"])
    parameters = build_parameters(row["kind"], canonical["parameters"])
    signal_policy = SignalPolicy(**canonical["signal_policy"])
    return StrategySpecV1(
        strategy_id=row["strategy_id"],
        version=row["version"],
        schema_version=row["schema_version"],
        name=row["name"],
        kind=row["kind"],
        parameters=parameters,
        signal_policy=signal_policy,
        created_at_utc=from_naive_utc(row["created_at_utc"]),
        checksum=row["checksum"],
        canonical_json=row["canonical_json"],
    )


class DuckDBStrategySpecRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, spec: StrategySpecV1) -> StrategySpecV1:
        with connect(self._settings) as connection:
            connection.execute(
                f"""
                INSERT INTO strategy_specs ({", ".join(_COLUMNS)})
                VALUES ({", ".join("?" for _ in _COLUMNS)})
                """,
                [
                    spec.strategy_id,
                    spec.version,
                    spec.schema_version,
                    spec.name,
                    spec.kind,
                    spec.canonical_json,
                    spec.checksum,
                    to_naive_utc(spec.created_at_utc),
                ],
            )
        return spec

    def get(self, strategy_id: str, version: int) -> StrategySpecV1 | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM strategy_specs
                WHERE strategy_id = ? AND version = ?
                """,
                [strategy_id, version],
            ).fetchone()
        if row is None:
            return None
        return _row_to_spec(dict(zip(_COLUMNS, row, strict=True)))

    def list(self, *, limit: int, offset: int) -> Page[StrategySpecV1]:
        with connect(self._settings) as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM strategy_specs").fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM strategy_specs
                ORDER BY created_at_utc, strategy_id, version
                LIMIT ? OFFSET ?
                """,
                [limit, offset],
            ).fetchall()
        items = [_row_to_spec(dict(zip(_COLUMNS, row, strict=True))) for row in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)
