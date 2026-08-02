from typing import Any

import duckdb
import pytest

from app.application.strategy_spec_service import create_strategy_spec
from app.infrastructure.db.migration_runner import run_migrations
from app.infrastructure.db.strategy_spec_repository import DuckDBStrategySpecRepository
from app.infrastructure.settings import Settings


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    db_path = tmp_path / "test.duckdb"
    connection = duckdb.connect(str(db_path))
    run_migrations(connection)
    connection.close()
    return Settings(database_path=str(db_path))


def _sequential_ids() -> Any:
    counter = iter(range(1, 1000))

    def factory() -> str:
        return f"strat-{next(counter)}"

    return factory


def test_create_and_get_round_trip(settings: Settings) -> None:
    repository = DuckDBStrategySpecRepository(settings)
    spec = create_strategy_spec(
        repository,
        name="SMA crossover 10/30",
        kind="sma_crossover",
        fast_window=10,
        slow_window=30,
        price_field="close",
        signal_time="bar_close",
        eligible_after_bars=30,
        long_only=True,
        id_factory=_sequential_ids(),
    )

    fetched = repository.get(spec.strategy_id, spec.version)

    assert fetched == spec


def test_get_returns_none_for_unknown(settings: Settings) -> None:
    repository = DuckDBStrategySpecRepository(settings)
    assert repository.get("does-not-exist", 1) is None


def test_list_paginates(settings: Settings) -> None:
    repository = DuckDBStrategySpecRepository(settings)
    ids = _sequential_ids()
    for _ in range(3):
        create_strategy_spec(
            repository,
            name="SMA crossover",
            kind="sma_crossover",
            fast_window=10,
            slow_window=30,
            price_field="close",
            signal_time="bar_close",
            eligible_after_bars=30,
            long_only=True,
            id_factory=ids,
        )

    page = repository.list(limit=2, offset=0)

    assert page.total == 3
    assert len(page.items) == 2
