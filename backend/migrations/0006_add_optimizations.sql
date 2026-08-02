CREATE TABLE optimizations (
    optimization_id VARCHAR PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    checksum VARCHAR NOT NULL,
    dataset_id VARCHAR NOT NULL REFERENCES datasets (dataset_id),
    instrument_id VARCHAR NOT NULL REFERENCES instruments (instrument_id),
    base_strategy_name VARCHAR NOT NULL,
    fast_window_grid VARCHAR NOT NULL,
    slow_window_grid VARCHAR NOT NULL,
    train_start DATE NOT NULL,
    train_end DATE NOT NULL,
    validation_start DATE NOT NULL,
    validation_end DATE NOT NULL,
    holdout_start DATE NOT NULL,
    holdout_end DATE NOT NULL,
    capital_amount DECIMAL(18, 6) NOT NULL,
    capital_currency VARCHAR NOT NULL,
    position_sizing_fraction DECIMAL(18, 6) NOT NULL,
    quantity_increment DECIMAL(18, 6) NOT NULL,
    money_scale INTEGER NOT NULL,
    annualization_basis INTEGER NOT NULL,
    risk_free_rate DECIMAL(18, 6) NOT NULL,
    objective_metric_key VARCHAR NOT NULL,
    tie_break_rule VARCHAR NOT NULL,
    max_candidate_count INTEGER NOT NULL,
    candidate_count INTEGER NOT NULL,
    rejected_count INTEGER NOT NULL,
    manifest_json VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    failure_code VARCHAR,
    selected_candidate_id VARCHAR,
    selection_reason VARCHAR,
    selection_audit_json VARCHAR,
    selected_at_utc TIMESTAMP,
    holdout_run_id VARCHAR,
    holdout_objective_status VARCHAR,
    holdout_objective_value VARCHAR,
    holdout_objective_reason VARCHAR,
    created_at_utc TIMESTAMP NOT NULL,
    started_at_utc TIMESTAMP,
    finished_at_utc TIMESTAMP,
    CHECK (
        status IN (
            'created', 'validating', 'running_train_validation', 'selecting',
            'running_holdout', 'completed', 'failed', 'cancelled'
        )
    ),
    CHECK (holdout_objective_status IS NULL OR holdout_objective_status IN ('available', 'not_available'))
);

CREATE TABLE optimization_candidates (
    candidate_id VARCHAR PRIMARY KEY,
    optimization_id VARCHAR NOT NULL,
    sequence INTEGER NOT NULL,
    fast_window INTEGER NOT NULL,
    slow_window INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    rejection_reason VARCHAR,
    strategy_id VARCHAR,
    strategy_version INTEGER,
    train_run_id VARCHAR,
    validation_run_id VARCHAR,
    objective_status VARCHAR,
    objective_value VARCHAR,
    objective_reason VARCHAR,
    warning_count INTEGER NOT NULL DEFAULT 0,
    created_at_utc TIMESTAMP NOT NULL,
    CHECK (status IN ('pending', 'rejected', 'completed', 'failed')),
    CHECK (objective_status IS NULL OR objective_status IN ('available', 'not_available')),
    UNIQUE (optimization_id, sequence)
);

CREATE INDEX idx_optimization_candidates_optimization_id
    ON optimization_candidates (optimization_id, sequence);
