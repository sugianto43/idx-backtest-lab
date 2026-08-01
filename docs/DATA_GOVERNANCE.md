# Data Governance and Research Integrity

## Provenance minimum

Every imported dataset must retain: provider/source name, license or terms reference, retrieval/import timestamp, source file/API identifier, checksum where applicable, covered instruments/dates, bar interval, timezone, adjustment status, validation outcome, and importer version.

## Data layers

1. **Raw:** byte-preserved or equivalent immutable source record.
2. **Normalized:** parsed, standardized records with validation results.
3. **Derived:** indicators, universes, and artifacts reproducible from named normalized inputs.

Never overwrite a layer in place. New ingestion or transformation creates a new version linked to its parent.

## Required validation

- Instrument identifiers resolve to a stable internal ID and effective-dated ticker mapping.
- Bars are unique and chronologically ordered per instrument/interval.
- Timestamps have an explicit timezone/session interpretation.
- OHLC relationships and volume values are valid, or deviations are recorded as quality events.
- Missing sessions, trading halts, and incomplete coverage are represented rather than fabricated.
- Adjustment handling for splits, dividends, rights issues, ticker changes, and delistings is explicit.

## Bias controls

- Signals may only consume data known before their declared decision time.
- Avoid survivorship bias by maintaining historical universe membership and delisting treatment.
- Prevent data snooping: optimization tasks must separate training, validation, and holdout evaluation.
- Persist all assumptions that can alter fills, portfolio values, or metrics.

## Handling uncertainty

If a data rule is unknown, retain the data with an explicit warning where safe, or reject it where use would falsify a result. Never silently substitute values or infer corporate actions.
