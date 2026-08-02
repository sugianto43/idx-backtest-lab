ALTER TABLE strategy_specs RENAME TO strategy_specs_pre_0007;

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
    CHECK (kind IN ('sma_crossover', 'rsi_threshold', 'macd_crossover', 'bollinger_breakout')),
    CHECK (version > 0)
);

INSERT INTO strategy_specs SELECT * FROM strategy_specs_pre_0007;

DROP TABLE strategy_specs_pre_0007;
