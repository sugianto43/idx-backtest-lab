import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
_FILENAME_PATTERN = re.compile(r"^(?P<version>\d+)_(?P<name>[a-z0-9_]+)\.sql$")

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str
    checksum: str


def _split_statements(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def discover_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> tuple[Migration, ...]:
    if not migrations_dir.is_dir():
        raise MigrationError(f"Migrations directory not found: {migrations_dir}")

    migrations: list[Migration] = []
    seen_versions: set[int] = set()
    for path in sorted(migrations_dir.glob("*.sql")):
        match = _FILENAME_PATTERN.match(path.name)
        if match is None:
            raise MigrationError(f"Malformed migration filename: {path.name}")

        version = int(match.group("version"))
        if version in seen_versions:
            raise MigrationError(f"Duplicate migration version: {version}")
        seen_versions.add(version)

        content = path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        migrations.append(
            Migration(
                version=version,
                name=match.group("name"),
                sql=content.decode("utf-8"),
                checksum=checksum,
            )
        )

    migrations.sort(key=lambda migration: migration.version)
    for index, migration in enumerate(migrations, start=1):
        if migration.version != index:
            raise MigrationError(
                "Migration versions must be contiguous starting at 1; "
                f"found version {migration.version} at position {index}"
            )

    return tuple(migrations)


def run_migrations(connection: Any, migrations_dir: Path = MIGRATIONS_DIR) -> None:
    migrations = discover_migrations(migrations_dir)

    ledger_exists = connection.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"
    ).fetchone()

    applied: dict[int, str] = {}
    if ledger_exists is not None:
        applied = dict(
            connection.execute("SELECT version, checksum FROM schema_migrations").fetchall()
        )

    max_known_version = migrations[-1].version if migrations else 0
    unknown_versions = sorted(version for version in applied if version > max_known_version)
    if unknown_versions:
        raise MigrationError(f"Database has migrations newer than known: {unknown_versions}")

    for migration in migrations:
        if migration.version in applied:
            if applied[migration.version] != migration.checksum:
                raise MigrationError(
                    f"Checksum mismatch for applied migration {migration.version} "
                    f"({migration.name}); migration history may have been edited"
                )
            continue

        logger.info("Applying migration %s: %s", migration.version, migration.name)
        try:
            connection.execute("BEGIN TRANSACTION")
            for statement in _split_statements(migration.sql):
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations (version, name, applied_at_utc, checksum) "
                "VALUES (?, ?, ?, ?)",
                [
                    migration.version,
                    migration.name,
                    datetime.now(UTC).replace(tzinfo=None),
                    migration.checksum,
                ],
            )
            connection.execute("COMMIT")
        except Exception as exc:
            connection.execute("ROLLBACK")
            logger.exception(
                "Migration %s (%s) failed; rolled back", migration.version, migration.name
            )
            raise MigrationError(
                f"Migration {migration.version} ({migration.name}) failed"
            ) from exc
