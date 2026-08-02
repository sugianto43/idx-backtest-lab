# CSV Ingestion Contract

> **Internal contract, not a user-facing upload format.** Since ADR-011, there is no HTTP endpoint that accepts a user-supplied CSV file. This document now describes the byte format the Yahoo Finance provider adapter (ADR-010) produces internally and feeds through `ImportDatasetUseCase` — it remains the authoritative reference for that use case's validation rules and for any future provider adapter, per ADR-003.

## Scope

This is the provider-neutral initial format for daily and intraday OHLCV import. A file represents one dataset version and must contain one header row plus data rows. The importer must reject ambiguous or malformed files rather than guessing semantics.

## Required upload metadata

| Field | Requirements |
| --- | --- |
| `name` | Non-empty dataset label. |
| `source_name` | Human-readable legal/source label. |
| `source_reference` | Optional provider, export, or file reference; no credentials. |
| `license_reference` | Required URL/text reference to applicable terms or a declared `user_supplied_unknown` value. |
| `bar_interval` | Explicit canonical interval such as `1d`, `1h`, or `5m`. |
| `timezone` | IANA timezone for timestamps, or `UTC`. |
| `adjustment_policy` | One of `raw`, `split_adjusted`, `total_return_adjusted`, or `unknown`. `unknown` imports only with a prominent warning and cannot silently become another value. |
| `instrument_mapping_policy` | `provided_internal_id` or `ticker_as_of_import`; ticker mapping resolution is completed in TASK-005. |

## Required CSV columns

Columns are case-sensitive and comma-delimited UTF-8:

```text
timestamp,instrument_identifier,open,high,low,close,volume
```

- `timestamp`: ISO 8601 timestamp with offset, or date-only ISO `YYYY-MM-DD` only for `1d` data. Date-only rows are interpreted using supplied timezone and recorded with that interpretation.
- `instrument_identifier`: non-empty source identifier/ticker. This is not yet a permanent instrument ID.
- `open`, `high`, `low`, `close`: positive decimal strings using `.` decimal separator; no thousand separators or currency symbols.
- `volume`: non-negative whole-number string. Zero is retained and creates a quality warning unless an explicit policy later says otherwise.

Optional columns are `source_row_id` and `currency`. Extra columns are rejected in the initial contract to prevent silently ignored semantics.

## Row validation

For every row, require `low <= min(open, close) <= max(open, close) <= high`, finite values, valid timestamp, and a unique `(instrument_identifier, timestamp, bar_interval)` key inside the file. Rows must be strictly chronological per instrument after normalization. Duplicate, invalid, unparseable, or mixed-interval rows reject the entire import.

## Import result

The system creates a new immutable dataset version with raw-file checksum, metadata, row counts, coverage dates, source identifiers, validation events, and normalized bars. It never overwrites a prior dataset. A valid import can carry warnings; any rejected import creates an audit record without usable normalized bars.

## Non-goals

Corporate actions, currency conversion, ticker-history resolution, exchange-session validation, and provider-specific field mapping are deferred to later tasks.
