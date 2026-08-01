CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    applied_at_utc TIMESTAMP NOT NULL,
    checksum VARCHAR NOT NULL
);

CREATE TABLE datasets (
    dataset_id VARCHAR PRIMARY KEY,
    version INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    source_name VARCHAR NOT NULL,
    source_reference VARCHAR,
    license_reference VARCHAR,
    content_checksum VARCHAR,
    bar_interval VARCHAR NOT NULL,
    timezone VARCHAR NOT NULL,
    adjustment_policy VARCHAR NOT NULL,
    coverage_start_date DATE,
    coverage_end_date DATE,
    created_at_utc TIMESTAMP NOT NULL,
    validation_status VARCHAR NOT NULL,
    validation_summary VARCHAR,
    CHECK (validation_status IN ('pending', 'valid', 'warning', 'rejected')),
    CHECK (
        coverage_start_date IS NULL
        OR coverage_end_date IS NULL
        OR coverage_start_date <= coverage_end_date
    )
);

CREATE TABLE backtest_runs (
    run_id VARCHAR PRIMARY KEY,
    dataset_id VARCHAR NOT NULL REFERENCES datasets (dataset_id),
    strategy_spec_version VARCHAR NOT NULL,
    engine_version VARCHAR NOT NULL,
    configuration_json VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    created_at_utc TIMESTAMP NOT NULL,
    started_at_utc TIMESTAMP,
    finished_at_utc TIMESTAMP,
    warning_count INTEGER NOT NULL DEFAULT 0,
    failure_code VARCHAR,
    CHECK (status IN ('created', 'running', 'completed', 'failed', 'cancelled')),
    CHECK (warning_count >= 0)
);

CREATE INDEX idx_backtest_runs_dataset_id ON backtest_runs (dataset_id);

CREATE INDEX idx_backtest_runs_created_at_utc ON backtest_runs (created_at_utc);
