# ADR-001: Initial technology boundaries

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

The product needs a local-first research workflow with a browser interface, typed API, analytical local storage, and a backtesting engine. Financial behavior must remain independent of framework and engine details.

## Decision

Use FastAPI/Python for the API, Next.js/TypeScript for the browser UI, DuckDB for local analytical persistence, Docker Compose for local orchestration, and Backtrader only behind an internal execution-engine adapter.

## Consequences

- Python is suitable for research-oriented computation and the planned engine integration.
- Next.js provides a typed browser application boundary.
- DuckDB is appropriate for local, analytical data but its schema/migration strategy still requires a dedicated decision.
- Backtrader behavior must be translated to product-neutral contracts and covered by adapter tests.
- This decision does not select a market-data provider, adjustment policy, or live deployment approach.

## Reversibility

Moderate. Infrastructure adapters and public product contracts must isolate these choices. Changes require a new ADR and migration plan once persistent data or public APIs exist.
