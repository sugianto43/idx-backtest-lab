from app.domain.backtest_run import BacktestRunStatus


class ApplicationError(Exception):
    pass


class BacktestRunNotFoundError(ApplicationError):
    def __init__(self, run_id: str) -> None:
        super().__init__(f"Backtest run not found: {run_id}")
        self.run_id = run_id


class UnknownDatasetReferenceError(ApplicationError):
    def __init__(self, dataset_id: str) -> None:
        super().__init__(f"Unknown dataset reference: {dataset_id}")
        self.dataset_id = dataset_id


class InvalidStatusTransitionError(ApplicationError):
    def __init__(self, current: BacktestRunStatus, next_status: BacktestRunStatus) -> None:
        super().__init__(f"Cannot transition backtest run from {current} to {next_status}")
        self.current = current
        self.next_status = next_status


class StaleRunStatusError(ApplicationError):
    def __init__(self, run_id: str, expected: BacktestRunStatus, actual: BacktestRunStatus) -> None:
        super().__init__(f"Run {run_id} expected status {expected} but found {actual}")
        self.run_id = run_id
        self.expected = expected
        self.actual = actual


class CsvContractViolation(ApplicationError):
    def __init__(self, code: str, message: str, row_number: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.row_number = row_number


class DatasetReimportConflictError(ApplicationError):
    def __init__(self, existing_dataset_id: str) -> None:
        super().__init__(f"An identical dataset already exists: {existing_dataset_id}")
        self.existing_dataset_id = existing_dataset_id


class DatasetNotFoundError(ApplicationError):
    def __init__(self, dataset_id: str) -> None:
        super().__init__(f"Dataset not found: {dataset_id}")
        self.dataset_id = dataset_id


class InstrumentNotFoundError(ApplicationError):
    def __init__(self, instrument_id: str) -> None:
        super().__init__(f"Instrument not found: {instrument_id}")
        self.instrument_id = instrument_id


class AliasOverlapError(ApplicationError):
    def __init__(self, symbol: str, exchange_code: str) -> None:
        super().__init__(
            f"An alias for {symbol} on {exchange_code} already exists in an overlapping date range"
        )
        self.symbol = symbol
        self.exchange_code = exchange_code


class MappingOverlapError(ApplicationError):
    def __init__(self, dataset_id: str, source_instrument_identifier: str) -> None:
        super().__init__(
            f"A mapping for {source_instrument_identifier} in dataset {dataset_id} "
            "already exists in an overlapping date range"
        )
        self.dataset_id = dataset_id
        self.source_instrument_identifier = source_instrument_identifier


class CorporateActionNotFoundError(ApplicationError):
    def __init__(self, event_id: str) -> None:
        super().__init__(f"Corporate action not found: {event_id}")
        self.event_id = event_id


class StrategySpecNotFoundError(ApplicationError):
    def __init__(self, strategy_id: str, version: int) -> None:
        super().__init__(f"Strategy spec not found: {strategy_id}@{version}")
        self.strategy_id = strategy_id
        self.version = version
