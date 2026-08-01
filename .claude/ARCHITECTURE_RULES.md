# Architecture Rules

## Target shape

The system separates presentation, application orchestration, domain rules, and infrastructure adapters. Dependencies point inward: UI/API and adapters depend on application/domain contracts; domain code depends on neither FastAPI, DuckDB, Backtrader, nor browser frameworks.

## Boundaries

- **Frontend** renders views and calls versioned API contracts. It does not reproduce financial calculations or query DuckDB.
- **API layer** validates transport input, authenticates/authorizes when introduced, maps errors, and invokes application use cases.
- **Application layer** coordinates use cases, transactions, and ports; it owns no framework-specific request/response objects.
- **Domain layer** owns invariant-preserving entities, value objects, calculations, and policies.
- **Infrastructure layer** implements ports for persistence, data ingestion, engine execution, files, clocks, and external services.
- **Engine adapter** translates product-neutral strategy/run models to and from Backtrader. No engine types cross the adapter boundary.

## Mandatory rules

1. Backtest input manifests and output artifacts are immutable. Rerunning creates a new run ID.
2. Persist timestamps in UTC and retain exchange-local session date/time where relevant. Use `Asia/Jakarta` only when an explicit IDX-local interpretation is required.
3. Assign stable IDs internally; tickers are mutable external identifiers and require effective-dated history.
4. Store raw source data separately from normalized and derived data. Retain provenance, ingestion time, checksum/version, and adjustment policy.
5. Validate domain invariants at boundaries: e.g. chronological bars, non-negative volume, valid OHLC relationships, unique run inputs.
6. Use explicit ports/interfaces for repositories, data sources, and engine execution; do not embed SQL or engine calls in routes or domain entities.
7. Version public APIs, persisted schemas, strategy specifications, and result manifests before compatibility matters.
8. Add observability around imports and runs: correlation/run IDs, structured logs, timings, warnings, and actionable failure reasons.

## Data and computation

- Prefer decimal/integer representations for money and deterministic rounding rules.
- Keep raw input immutable; record transformations as reproducible steps.
- Metrics must state their formula, annualization basis, risk-free-rate assumption, and treatment of missing sessions.
- A run must reject or flag incomplete inputs rather than silently filling values that affect results.

## ADR trigger

Create an ADR before introducing an external dependency, changing a public contract, choosing a data source or adjustment policy, altering simulation semantics, or making an irreversible persistence decision.
