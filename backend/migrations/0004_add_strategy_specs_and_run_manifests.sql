CREATE TABLE strategy_specs (
    strategy_id VARCHAR NOT NULL,
    version INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    canonical_json VARCHAR NOT NULL,
    checksum VARCHAR NOT NULL,
    created_at_utc TIMESTAMP NOT NULL,
    PRIMARY KEY (strategy_id, version),
    CHECK (kind IN ('sma_crossover')),
    CHECK (version > 0)
);

ALTER TABLE backtest_runs ADD COLUMN schema_version INTEGER;

ALTER TABLE backtest_runs ADD COLUMN manifest_checksum VARCHAR;

ALTER TABLE backtest_runs ADD COLUMN strategy_id VARCHAR;

ALTER TABLE backtest_runs ADD COLUMN strategy_version INTEGER;

CREATE INDEX idx_backtest_runs_strategy_ref ON backtest_runs (strategy_id, strategy_version);
