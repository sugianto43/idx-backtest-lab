CREATE TABLE run_artifact_bundles (
    bundle_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL UNIQUE REFERENCES backtest_runs (run_id),
    artifact_schema_version INTEGER NOT NULL,
    checksum VARCHAR NOT NULL,
    terminal_status VARCHAR NOT NULL,
    provenance_json VARCHAR NOT NULL,
    event_count INTEGER NOT NULL,
    snapshot_count INTEGER NOT NULL,
    metric_count INTEGER NOT NULL,
    created_at_utc TIMESTAMP NOT NULL,
    CHECK (terminal_status IN ('completed', 'failed')),
    CHECK (artifact_schema_version > 0)
);

CREATE TABLE run_order_events (
    event_id VARCHAR PRIMARY KEY,
    bundle_id VARCHAR NOT NULL REFERENCES run_artifact_bundles (bundle_id),
    run_id VARCHAR NOT NULL,
    sequence INTEGER NOT NULL,
    instrument_id VARCHAR NOT NULL,
    side VARCHAR NOT NULL,
    created_at_utc TIMESTAMP NOT NULL,
    intended_quantity INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    rejection_reason VARCHAR,
    CHECK (side IN ('buy', 'sell')),
    CHECK (status IN ('filled', 'rejected'))
);

CREATE INDEX idx_run_order_events_bundle_id ON run_order_events (bundle_id, sequence);

CREATE TABLE run_fill_events (
    fill_id VARCHAR PRIMARY KEY,
    bundle_id VARCHAR NOT NULL REFERENCES run_artifact_bundles (bundle_id),
    run_id VARCHAR NOT NULL,
    sequence INTEGER NOT NULL,
    order_id VARCHAR NOT NULL,
    instrument_id VARCHAR NOT NULL,
    side VARCHAR NOT NULL,
    filled_at_utc TIMESTAMP NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(18, 6) NOT NULL,
    currency VARCHAR NOT NULL,
    commission DECIMAL(18, 6) NOT NULL,
    tax DECIMAL(18, 6) NOT NULL,
    slippage DECIMAL(18, 6) NOT NULL,
    CHECK (side IN ('buy', 'sell'))
);

CREATE INDEX idx_run_fill_events_bundle_id ON run_fill_events (bundle_id, sequence);

CREATE TABLE run_position_events (
    position_event_id VARCHAR PRIMARY KEY,
    bundle_id VARCHAR NOT NULL REFERENCES run_artifact_bundles (bundle_id),
    run_id VARCHAR NOT NULL,
    sequence INTEGER NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    instrument_id VARCHAR NOT NULL,
    quantity INTEGER NOT NULL,
    average_cost DECIMAL(18, 6) NOT NULL,
    reason VARCHAR NOT NULL
);

CREATE INDEX idx_run_position_events_bundle_id ON run_position_events (bundle_id, sequence);

CREATE TABLE run_cash_events (
    cash_event_id VARCHAR PRIMARY KEY,
    bundle_id VARCHAR NOT NULL REFERENCES run_artifact_bundles (bundle_id),
    run_id VARCHAR NOT NULL,
    sequence INTEGER NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    currency VARCHAR NOT NULL,
    cash_before DECIMAL(18, 6) NOT NULL,
    cash_after DECIMAL(18, 6) NOT NULL,
    reason VARCHAR NOT NULL
);

CREATE INDEX idx_run_cash_events_bundle_id ON run_cash_events (bundle_id, sequence);

CREATE TABLE run_warnings (
    warning_id VARCHAR PRIMARY KEY,
    bundle_id VARCHAR NOT NULL REFERENCES run_artifact_bundles (bundle_id),
    run_id VARCHAR NOT NULL,
    sequence INTEGER NOT NULL,
    code VARCHAR NOT NULL,
    message VARCHAR NOT NULL,
    instrument_id VARCHAR,
    timestamp_utc TIMESTAMP
);

CREATE INDEX idx_run_warnings_bundle_id ON run_warnings (bundle_id, sequence);

CREATE TABLE portfolio_snapshots (
    snapshot_id VARCHAR PRIMARY KEY,
    bundle_id VARCHAR NOT NULL REFERENCES run_artifact_bundles (bundle_id),
    run_id VARCHAR NOT NULL,
    sequence INTEGER NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    cash DECIMAL(18, 6) NOT NULL,
    holdings_value DECIMAL(18, 6) NOT NULL,
    total_equity DECIMAL(18, 6) NOT NULL,
    currency VARCHAR NOT NULL,
    valuation_status VARCHAR NOT NULL,
    valuation_reason VARCHAR,
    CHECK (valuation_status IN ('valid', 'not_available')),
    UNIQUE (bundle_id, sequence)
);

CREATE INDEX idx_portfolio_snapshots_bundle_id ON portfolio_snapshots (bundle_id, sequence);

CREATE TABLE run_metrics (
    metric_id VARCHAR PRIMARY KEY,
    bundle_id VARCHAR NOT NULL REFERENCES run_artifact_bundles (bundle_id),
    run_id VARCHAR NOT NULL,
    metric_key VARCHAR NOT NULL,
    value VARCHAR,
    status VARCHAR NOT NULL,
    reason VARCHAR,
    definition_version INTEGER NOT NULL,
    calculation_input_json VARCHAR NOT NULL,
    CHECK (status IN ('available', 'not_available')),
    UNIQUE (bundle_id, metric_key)
);

CREATE INDEX idx_run_metrics_bundle_id ON run_metrics (bundle_id);

CREATE TABLE reproducibility_manifests (
    manifest_id VARCHAR PRIMARY KEY,
    bundle_id VARCHAR NOT NULL UNIQUE REFERENCES run_artifact_bundles (bundle_id),
    run_id VARCHAR NOT NULL,
    canonical_json VARCHAR NOT NULL,
    checksum VARCHAR NOT NULL,
    created_at_utc TIMESTAMP NOT NULL
);
