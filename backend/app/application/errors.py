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
