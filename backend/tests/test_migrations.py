from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from app.infrastructure.db.migration_runner import (
    MigrationError,
    discover_migrations,
    run_migrations,
)


def test_discover_migrations_returns_ordered_contiguous_versions() -> None:
    migrations = discover_migrations()

    assert [migration.version for migration in migrations] == list(range(1, len(migrations) + 1))


def test_run_migrations_applies_all_and_records_ledger(tmp_path: Path) -> None:
    connection = duckdb.connect(str(tmp_path / "test.duckdb"))
    try:
        run_migrations(connection)

        rows = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
        migrations = discover_migrations()

        assert [row[0] for row in rows] == [migration.version for migration in migrations]
        assert [row[2] for row in rows] == [migration.checksum for migration in migrations]
    finally:
        connection.close()


def test_run_migrations_is_idempotent(tmp_path: Path) -> None:
    connection = duckdb.connect(str(tmp_path / "test.duckdb"))
    try:
        run_migrations(connection)
        before = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()

        run_migrations(connection)
        after = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()

        assert before == after
    finally:
        connection.close()


def test_run_migrations_fails_closed_on_checksum_mismatch(tmp_path: Path) -> None:
    connection = duckdb.connect(str(tmp_path / "test.duckdb"))
    try:
        run_migrations(connection)
        connection.execute("UPDATE schema_migrations SET checksum = 'tampered' WHERE version = 1")

        with pytest.raises(MigrationError):
            run_migrations(connection)
    finally:
        connection.close()


def test_discover_migrations_rejects_duplicate_version(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "0001_a.sql").write_text("SELECT 1;")
    (migrations_dir / "0001_b.sql").write_text("SELECT 1;")

    with pytest.raises(MigrationError):
        discover_migrations(migrations_dir)


def test_discover_migrations_rejects_malformed_filename(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "not_a_migration.sql").write_text("SELECT 1;")

    with pytest.raises(MigrationError):
        discover_migrations(migrations_dir)


def test_discover_migrations_rejects_non_contiguous_versions(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "0001_a.sql").write_text("SELECT 1;")
    (migrations_dir / "0003_b.sql").write_text("SELECT 1;")

    with pytest.raises(MigrationError):
        discover_migrations(migrations_dir)


def test_run_migrations_rejects_database_newer_than_known(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "0001_a.sql").write_text(
        "CREATE TABLE schema_migrations ("
        "version INTEGER PRIMARY KEY, name VARCHAR NOT NULL, "
        "applied_at_utc TIMESTAMP NOT NULL, checksum VARCHAR NOT NULL);"
    )

    connection = duckdb.connect(str(tmp_path / "future.duckdb"))
    try:
        run_migrations(connection, migrations_dir)
        connection.execute(
            "INSERT INTO schema_migrations VALUES (?, ?, ?, ?)",
            [2, "future_migration", datetime.now(UTC).replace(tzinfo=None), "bogus"],
        )

        with pytest.raises(MigrationError):
            run_migrations(connection, migrations_dir)
    finally:
        connection.close()
