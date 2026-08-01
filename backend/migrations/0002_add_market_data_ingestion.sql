ALTER TABLE datasets ADD COLUMN instrument_mapping_policy VARCHAR DEFAULT 'ticker_as_of_import';

CREATE TABLE normalized_bars (
    bar_id VARCHAR PRIMARY KEY,
    dataset_id VARCHAR NOT NULL REFERENCES datasets (dataset_id),
    source_instrument_identifier VARCHAR NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    bar_interval VARCHAR NOT NULL,
    open DECIMAL(18, 6) NOT NULL,
    high DECIMAL(18, 6) NOT NULL,
    low DECIMAL(18, 6) NOT NULL,
    close DECIMAL(18, 6) NOT NULL,
    volume BIGINT NOT NULL,
    currency VARCHAR,
    source_row_id VARCHAR,
    CHECK (volume >= 0),
    CHECK (open > 0 AND high > 0 AND low > 0 AND close > 0),
    CHECK (low <= open AND low <= close AND high >= open AND high >= close AND low <= high),
    UNIQUE (dataset_id, source_instrument_identifier, timestamp_utc, bar_interval)
);

CREATE INDEX idx_normalized_bars_dataset_id ON normalized_bars (dataset_id);

CREATE TABLE dataset_imports (
    import_id VARCHAR PRIMARY KEY,
    dataset_id VARCHAR REFERENCES datasets (dataset_id),
    raw_filename VARCHAR NOT NULL,
    content_checksum VARCHAR NOT NULL,
    byte_size BIGINT NOT NULL,
    requested_metadata VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    row_count INTEGER NOT NULL,
    accepted_row_count INTEGER NOT NULL,
    warning_count INTEGER NOT NULL,
    error_count INTEGER NOT NULL,
    started_at_utc TIMESTAMP NOT NULL,
    finished_at_utc TIMESTAMP NOT NULL,
    failure_code VARCHAR,
    failure_row_number INTEGER,
    CHECK (status IN ('pending', 'valid', 'warning', 'rejected')),
    CHECK (row_count >= 0 AND accepted_row_count >= 0 AND warning_count >= 0 AND error_count >= 0)
);

CREATE INDEX idx_dataset_imports_dataset_id ON dataset_imports (dataset_id);

CREATE TABLE dataset_validation_events (
    event_id VARCHAR PRIMARY KEY,
    import_id VARCHAR NOT NULL REFERENCES dataset_imports (import_id),
    dataset_id VARCHAR REFERENCES datasets (dataset_id),
    severity VARCHAR NOT NULL,
    code VARCHAR NOT NULL,
    message VARCHAR NOT NULL,
    source_row_number INTEGER,
    created_at_utc TIMESTAMP NOT NULL,
    CHECK (severity IN ('warning', 'error'))
);

CREATE INDEX idx_dataset_validation_events_dataset_id ON dataset_validation_events (dataset_id);

CREATE INDEX idx_dataset_validation_events_import_id ON dataset_validation_events (import_id);
