# ADR-002: Local persistence and schema evolution

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

The application needs local analytical persistence for dataset provenance, normalized market data, immutable backtest manifests, and artifacts. These records must remain understandable and safely evolvable as the product develops.

## Decision

Use one application-owned DuckDB database per local workspace. Manage its schema with ordered, append-only SQL migration files tracked in source control and a schema-version ledger in the database. Apply migrations transactionally where supported and fail before application startup/use if the database is newer than the application knows how to handle.

Access persistence only through application-owned repository ports. DuckDB connection, SQL, migration execution, paths, and serialization live in infrastructure adapters.

## Consequences

- Local portability and analytical queries are straightforward.
- An explicit database path and backup/export guidance will be needed.
- Migration files become part of the compatibility contract and cannot be edited after release; corrections require new migrations.
- DuckDB remains a single-workspace/local-store choice, not a multi-user server database.
- Data-provider-specific raw formats remain filesystem/source artifacts; the database stores provenance and normalized records after later ingestion work.

## Rejected alternatives

- **In-memory-only state:** fails reproducibility and audit requirements.
- **ORM-first schema ownership:** adds abstraction before the analytical schema and migrations are understood; direct parameterized SQL behind repository ports is preferred initially.
- **Hosted relational database:** out of scope for the local-first release.

## Reversibility

Moderate. Repository ports reduce coupling, but persisted data requires an export/migration plan before changing storage technology.
