# Project Memory

## Status

Phase 2 — Application implementation has begun. `TASK-001` is implemented and verified:

- Backend: FastAPI on Python 3.13, dependency-free `GET /health` returning `{"status":"ok"}`. Quality tooling: `ruff` (format + lint), `mypy --strict`, `pytest` (with `httpx` for `TestClient`). Direct dependencies pinned in `backend/requirements.txt` / `backend/requirements-dev.txt`.
- Frontend: Next.js 16.2.12 (App Router) + React 19.2.4 + strict TypeScript, minimal accessible landing page at `/`. Quality tooling: ESLint (`eslint-config-next` + `eslint-config-prettier`), Prettier, `tsc --noEmit`, Vitest + Testing Library.
- `docker-compose.yml` at repo root defines `api` (port 8000) and `web` (port 3000) development services; frontend `node_modules` is an isolated named volume. Both images build and serve correctly when run directly (verified via `docker run` on alternate host ports, since ports 3000/8000 were occupied by unrelated pre-existing host processes during verification).
- No database, market-data, strategy, or auth code exists yet — out of TASK-001 scope by design.

Known risk: `npm audit` reports 3 high-severity transitive advisories (postcss, sharp) pulled in by the pinned `next@16.2.12` release itself; no fix is available without downgrading Next.js to a much older major version, which is out of scope. Revisit when a newer Next.js patch/minor release addresses this.

`TASK-002` has been specified but not implemented. It defines the initial backend application boundary, health endpoints, correlation IDs, and safe API error handling; it deliberately excludes persistence and market-data work.

`TASK-003` has been specified but not implemented. ADR-002 selects an application-owned local DuckDB database, ordered append-only SQL migrations, and repository ports that isolate database details. The initial persistence scope is dataset provenance metadata and immutable run-manifest envelopes only; no market bars or backtest results are yet stored.

`TASK-004` has been specified but not implemented. ADR-003 selects provider-neutral local CSV ingestion for the first data workflow. It requires user-supplied source/license metadata, explicit interval/timezone/adjustment policy, immutable provenance, and fail-closed validation; provider APIs and bundled market data remain prohibited.

`TASK-005` has been specified but not implemented. ADR-004 defines immutable internal instrument IDs, effective-dated ticker aliases, and corporate-action evidence records. No automatic symbol resolution, price adjustment, or portfolio/event economics is authorized at this stage.

`TASK-006` has been specified but not implemented. ADR-005 defines versioned immutable strategy specifications and fully materialized run manifests with canonical JSON/checksums. Strategy v1 is declarative `sma_crossover`; run creation validates research assumptions but does not run an engine or create results.

`TASK-007` has been specified but not implemented. ADR-006 selects Backtrader only behind a product-neutral infrastructure adapter. V1 uses close-derived SMA crossover signals with next-bar-open fills and deterministic raw execution events; durable artifacts and metrics remain TASK-008 work.

`TASK-008` has been specified but not implemented. ADR-007 requires one immutable artifact bundle per terminal run, traceable through manifest/dataset/engine checksums. V1 metrics use explicit definitions and return `not_available` rather than inferred values; browser-side financial calculations remain prohibited.

`TASK-009` has been specified but not implemented. ADR-008 selects a strict TypeScript Next.js shell with one typed API-client boundary. The browser may display backend decimal strings and warnings but cannot calculate research/financial values.

`TASK-010` has been specified but not implemented. Its dashboard UX displays dataset provenance/import state and backend-produced run evidence, including explicit warnings and unavailable metric states. Charting, ranking, and browser-side financial computation remain prohibited.

`TASK-011` has been specified but not implemented. It limits browser authoring to the immutable declarative SMA-crossover strategy v1, with backend-authoritative validation and transparent timing/long-only constraints. It does not evaluate strategies or create runs.

`TASK-012` has been specified but not implemented. ADR-009 limits optimization to deterministic finite SMA grids with chronological train/validation/one-time sealed holdout evaluation. Every candidate and failure is immutable/auditable; the product must label output as research-only.

## Confirmed decisions

| Decision | Status | Source |
| --- | --- | --- |
| Product targets auditable IDX equity backtesting | Confirmed | Master Context |
| Planned stack: FastAPI, Next.js, DuckDB, Backtrader adapter, Docker Compose | Directional | Master Context |
| Backtest runs must be reproducible and immutable | Confirmed | Constitution |
| Financial correctness outranks convenience | Confirmed | Constitution |
| Initial technology boundaries are FastAPI, Next.js, DuckDB, Docker Compose, and a Backtrader adapter | Accepted | ADR-001 |

## Open decisions

- Historical data provider(s), licensing, source-of-truth policy, and refresh cadence.
- Adjustment policy for splits, dividends, rights issues, ticker changes, delistings, and suspensions.
- Exchange calendar, time-zone representation, and handling of special trading sessions.
- Exact transaction-cost, tax, slippage, liquidity, and price-limit models.
- Authentication, authorization, deployment, and backup model.
- Detailed package layout, schemas, and API contracts.

## Change protocol

Update this file whenever a decision, constraint, interface, or verified operational fact is likely to matter to future work. Use brief, dated facts. Move rationale-heavy choices to an ADR and link it here.

## Known risks

- Market-data rights, coverage, and quality may constrain the product design.
- Naive use of OHLCV data can create false performance through bias or unrealistic fills.
- Engine-specific behavior must not leak into product contracts.
