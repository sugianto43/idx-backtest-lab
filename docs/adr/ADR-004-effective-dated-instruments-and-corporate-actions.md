# ADR-004: Effective-dated instruments and corporate-action records

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Tickers can change, be reused, suspended, or delisted. Corporate actions can materially affect price/quantity interpretation. Treating a ticker as a permanent identity or automatically adjusting historical bars would create incorrect, non-auditable backtests.

## Decision

Use an immutable internal instrument ID as the primary identity. Store ticker symbols as effective-dated aliases linked to an instrument. Ingest corporate actions as immutable, source-provenanced records with an explicit status and no automatic mutation of imported bars. Adjustment and execution treatment is deferred until an approved policy and backtest configuration exist.

## Consequences

- Existing source identifiers from TASK-004 can be resolved later without overwriting raw history.
- Unknown/ambiguous ticker mappings remain visible and block workflows requiring reliable identity.
- Corporate-action records provide audit evidence but do not imply that prices, quantities, or portfolios have been adjusted.
- Strategy/backtest tasks must explicitly choose which approved event treatment they support.

## Reversibility

Moderate. Alias and event records are append-only evidence. Corrections create superseding records or resolution decisions, never destructive historical edits.
