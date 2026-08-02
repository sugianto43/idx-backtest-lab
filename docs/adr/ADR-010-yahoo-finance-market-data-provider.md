# ADR-010: Yahoo Finance market data provider adapter

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

ADR-003 deferred all provider APIs, scraping, and bundled market data until a specific provider, its licensing terms, and its adjustment semantics were formally decided, and required that any future provider adapter map to the *same* ingestion/application contracts (the CSV ingestion contract's validated, provenanced bar model) rather than introduce a second data path. The user has now explicitly chosen Yahoo Finance's public chart/history data as the first real provider.

Yahoo Finance's Terms of Service (https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) permit personal, non-commercial use of the data displayed on Yahoo Finance and explicitly prohibit systematic redistribution or resale of the data. There is no commercial agreement with Yahoo behind this integration — it is an unofficial client of Yahoo's public, undocumented but stable `query1.finance.yahoo.com` chart JSON endpoint (the same endpoint the popular `yfinance` Python package wraps). This is acceptable *only* because this product is a local-first, single-user, non-commercial research tool that never redistributes fetched data to third parties; it must not be repurposed as a hosted, multi-tenant, or commercial service without a real licensing review.

## Decision

Add a Yahoo Finance provider adapter, `app/infrastructure/market_data/yahoo_finance_provider.py`, that:

1. Fetches daily OHLCV history for one ticker over a caller-supplied date range via a direct HTTP call to Yahoo's public chart JSON endpoint, using only the Python standard library's `urllib.request` — deliberately not the `yfinance` package, to avoid pulling in its pandas/numpy dependency chain for what is otherwise a single JSON fetch and parse.
2. Uses Yahoo's split-adjusted `Close` column (not `Adj Close`, which is also dividend-adjusted) as the contract's single `close` value, and tags the resulting import with `adjustment_policy=split_adjusted` — an honest, specific claim, never `raw` or `unknown` when the true adjustment state is known.
3. Converts the fetched rows into exactly the existing `docs/CSV_INGESTION_CONTRACT.md` byte format in memory (header `timestamp,instrument_identifier,open,high,low,close,volume`, ISO date rows) and feeds them through the *existing, unmodified* `ImportDatasetUseCase` (the same code path `POST /api/v1/datasets:import` uses) — no new validation, normalization, or persistence logic is introduced. The provider adapter's only job is producing a conformant CSV; everything after that point is identical to a manually uploaded file.
4. Records `source_name="Yahoo Finance"` and `source_reference` as the exact ticker symbol and fetch parameters used, and `license_reference` as a fixed, explicit personal/non-commercial-use string pointing at Yahoo's Terms of Service — never a blank or `user_supplied_unknown` value, since the terms are specifically known here.

This is exposed as a new endpoint, `POST /api/v1/datasets:import-from-yahoo-finance` (ticker, date range, canonical dataset metadata), which is a thin translation layer in front of the existing import use case — not a parallel ingestion system.

## Consequences

- The product can now generate a real, provenance-complete dataset without a manual CSV export step, while reusing every existing validation/audit guarantee.
- The tool must never be deployed as a hosted or commercial service on top of this adapter without revisiting Yahoo's licensing terms — this is recorded here and in `RELEASE_NOTES.md` as a hard constraint, not a soft preference.
- No new third-party runtime dependency is added — the adapter uses only the Python standard library (`urllib.request`, `json`).
- No corporate-action, currency-conversion, or exchange-calendar logic is added — Yahoo's raw daily bars pass through the same CSV contract validation (row uniqueness, chronological order, OHLC relationships) as any other import.
- A future provider (e.g. a licensed IDX feed) still requires its own ADR and its own adapter mapping to the same contract, per ADR-003.

## Reversibility

High. The adapter is an isolated infrastructure module producing a conformant CSV payload for the existing import path; removing it deletes one file, one route, and its tests without touching the ingestion contract, schema, or any other provider.
