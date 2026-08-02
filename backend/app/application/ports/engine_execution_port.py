from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from app.domain.backtest_manifest import RunManifestV1
from app.domain.execution_result import ExecutionResult
from app.domain.market_data import NormalizedBar
from app.domain.strategy_spec import StrategySpecV1


class EngineExecutionPort(Protocol):
    def execute(
        self,
        *,
        manifest: RunManifestV1,
        manifest_checksum: str,
        strategy: StrategySpecV1,
        instrument_id: str,
        bars: list[NormalizedBar],
        id_factory: Callable[[], str],
        clock: Callable[[], datetime],
    ) -> ExecutionResult: ...
