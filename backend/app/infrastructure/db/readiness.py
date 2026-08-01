import logging

from app.infrastructure.db.connection import connect
from app.infrastructure.db.migration_runner import discover_migrations
from app.infrastructure.settings import Settings

logger = logging.getLogger(__name__)


def is_database_ready(settings: Settings) -> bool:
    try:
        expected_version_count = len(discover_migrations())
        with connect(settings) as connection:
            row = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
    except Exception:
        logger.exception("Database readiness check failed")
        return False

    applied_count = int(row[0]) if row is not None else 0
    return applied_count == expected_version_count
