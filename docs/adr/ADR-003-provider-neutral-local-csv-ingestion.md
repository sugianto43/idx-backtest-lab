# ADR-003: Provider-neutral local CSV ingestion

- **Status:** Superseded in part by ADR-011 (the manual-upload HTTP endpoint described here was removed; the underlying CSV contract and validation pipeline remain and are used internally by the Yahoo Finance adapter per ADR-010)
- **Date:** 2026-08-01

## Context

The product needs a first path for historical data, but no data provider, commercial terms, or redistribution rights have been approved. A provider-specific adapter would make unsupported assumptions and entangle licensing with the first vertical slice.

## Decision

The initial ingestion interface accepts a researcher-supplied local CSV file through a provider-neutral format contract. The user supplies source name, source reference, license/terms reference, timezone, interval, and adjustment policy with the file. The system stores raw file provenance/checksum and normalized validated bars separately.

Provider APIs, scraping, and bundled market data are explicitly deferred. A later provider adapter must map to the same ingestion/application contracts and receive a new ADR.

## Consequences

- The product can validate and audit data without claiming a licensed provider.
- Users retain responsibility for lawful data acquisition; the UI and API must make this visible.
- CSV dialect and column requirements become a documented compatibility contract.
- The ingestion model accommodates a future provider source without changing dataset/run provenance principles.

## Reversibility

High for source adapters; moderate for the canonical normalized-bar schema. New sources require contract tests and explicit license/provenance behavior.
