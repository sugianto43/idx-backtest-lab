# Technical Design Document

## System overview

The system is a local development stack composed of a Next.js browser client, FastAPI HTTP API, DuckDB analytical store, and an execution-engine adapter. The intended dependency direction is:

```text
Browser UI → HTTP API → Application use cases → Domain policies
                                  ↓
                  Infrastructure ports/adapters → DuckDB, files, Backtrader
```

Only adapters know framework, persistence, or engine APIs. The domain and application layers own product contracts and invariants.

## Proposed repository structure

```text
backend/
  app/
    api/             # routes, request/response schemas, error mapping
    application/     # use cases and port definitions
    domain/          # entities, value objects, policies, errors
    infrastructure/  # DuckDB, files, engine, source adapters
  tests/
frontend/
  app/               # pages/layouts
  components/
  lib/               # typed API client and UI-only helpers
  tests/
docs/
tasks/
```

## Runtime boundaries

### API

Expose versioned `/api/v1` resources. Keep a dependency-free `/health` endpoint for liveness. Routes validate HTTP payloads, call a use case, and map known application errors to stable error codes. Routes do not contain SQL, engine calls, metrics formulas, or execution logic.

### Domain and application

Use cases orchestrate: import dataset, validate data, create strategy, start run, retrieve artifacts, compare runs. Domain values include money, quantity, timestamp/session, dataset version, run manifest, and execution policy. Model business-rule failures as typed errors.

### Data

DuckDB is a local analytical store. Maintain raw input separately from normalized data and derived artifacts. Schema creation/evolution must be versioned and idempotent. Do not use DuckDB as a shared concurrent multi-user database without a separate decision.

### Engine adapter

An adapter translates product-neutral inputs to Backtrader and engine output back into product-neutral artifacts. It must explicitly map bar timing, fill assumptions, orders, fees/taxes/slippage, and rounding. The adapter has deterministic fixture tests.

### Frontend

Use typed API clients based on documented contracts. The frontend renders data, assumptions, and warnings; it does not independently calculate financial metrics. Loading/error/empty states are mandatory for each remote-data view.

## Cross-cutting design

- Persist UTC timestamps and retain exchange-local session representation when relevant.
- Treat ticker codes as effective-dated identifiers; never as permanent primary keys.
- Use Decimal/integer minor units for money and state rounding policy explicitly.
- Attach correlation IDs to imports/runs and record structured warnings and failure reasons.
- Run artifacts are append-only and identified by immutable run IDs.

## Deferred decisions

The data provider, adjustment handling, exchange calendar, cost/tax model, security model, exact schema, and API endpoints need separate ADRs/tasks before implementation.
