CREATE TABLE instruments (
    instrument_id VARCHAR PRIMARY KEY,
    instrument_type VARCHAR NOT NULL,
    display_name VARCHAR NOT NULL,
    currency VARCHAR,
    status VARCHAR NOT NULL,
    source_name VARCHAR NOT NULL,
    source_reference VARCHAR,
    created_at_utc TIMESTAMP NOT NULL,
    CHECK (instrument_type IN ('equity')),
    CHECK (status IN ('active', 'suspended', 'delisted', 'unknown'))
);

CREATE TABLE instrument_aliases (
    alias_id VARCHAR PRIMARY KEY,
    instrument_id VARCHAR NOT NULL REFERENCES instruments (instrument_id),
    symbol VARCHAR NOT NULL,
    exchange_code VARCHAR NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    source_name VARCHAR NOT NULL,
    source_reference VARCHAR,
    confidence VARCHAR NOT NULL,
    created_at_utc TIMESTAMP NOT NULL,
    CHECK (exchange_code IN ('IDX')),
    CHECK (confidence IN ('confirmed', 'tentative')),
    CHECK (effective_to IS NULL OR effective_from <= effective_to)
);

CREATE INDEX idx_instrument_aliases_instrument_id ON instrument_aliases (instrument_id);

CREATE INDEX idx_instrument_aliases_symbol_exchange ON instrument_aliases (symbol, exchange_code);

CREATE TABLE dataset_instrument_mappings (
    mapping_id VARCHAR PRIMARY KEY,
    dataset_id VARCHAR NOT NULL REFERENCES datasets (dataset_id),
    source_instrument_identifier VARCHAR NOT NULL,
    instrument_id VARCHAR NOT NULL REFERENCES instruments (instrument_id),
    effective_from DATE NOT NULL,
    effective_to DATE,
    decision_source VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    created_at_utc TIMESTAMP NOT NULL,
    CHECK (status IN ('resolved')),
    CHECK (effective_to IS NULL OR effective_from <= effective_to)
);

CREATE INDEX idx_dataset_instrument_mappings_lookup ON dataset_instrument_mappings (
    dataset_id, source_instrument_identifier
);

CREATE INDEX idx_dataset_instrument_mappings_instrument_id ON dataset_instrument_mappings (
    instrument_id
);

CREATE TABLE corporate_actions (
    event_id VARCHAR PRIMARY KEY,
    instrument_id VARCHAR NOT NULL REFERENCES instruments (instrument_id),
    event_type VARCHAR NOT NULL,
    effective_date DATE NOT NULL,
    announcement_date DATE,
    status VARCHAR NOT NULL,
    source_name VARCHAR NOT NULL,
    source_reference VARCHAR,
    payload_json VARCHAR NOT NULL,
    supersedes_event_id VARCHAR REFERENCES corporate_actions (event_id),
    created_at_utc TIMESTAMP NOT NULL,
    CHECK (
        event_type IN (
            'cash_dividend', 'stock_dividend', 'stock_split', 'reverse_split',
            'rights_issue', 'ticker_change', 'delisting', 'other'
        )
    ),
    CHECK (status IN ('reported', 'verified', 'superseded', 'rejected'))
);

CREATE INDEX idx_corporate_actions_instrument_id ON corporate_actions (instrument_id);
