from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb

from app.infrastructure.settings import Settings


def ensure_database_directory(database_path: str) -> None:
    parent = Path(database_path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect(settings: Settings) -> Iterator[Any]:
    ensure_database_directory(settings.database_path)
    connection = duckdb.connect(settings.database_path)
    try:
        yield connection
    finally:
        connection.close()
