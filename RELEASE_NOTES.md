# Release Notes — v1 (TASK-001 through TASK-013)

This is a local-first research tool for generating auditable evidence about
a single declarative trading strategy against historical Indonesian equity
data. It is not a trading platform, not a data provider, and not a source
of investment advice. Every backtest and optimization result is a
historical simulation only.

## What v1 can do

- Import provider-neutral daily OHLCV CSV data with strict validation,
  immutable versioning per import, and full provenance.
- Define stable instrument identities and effective-dated ticker aliases;
  map a dataset's raw identifiers to an instrument for a declared date
  range.
- Record corporate actions as immutable evidence (no price/share
  adjustment is calculated anywhere in the system).
- Author immutable, versioned `sma_crossover` strategy specifications
  (long-only, next-bar-open fills, bar-close signal timing).
- Create and execute a single-instrument backtest run, and retrieve its
  full immutable artifact bundle: order/fill/position/cash events,
  per-bar portfolio snapshots, 8 documented metrics (each explicitly
  `available` or `not_available` with a reason — never fabricated or
  zero-substituted), and a reproducibility manifest export.
- Run a finite-grid parameter optimization over `fast_window`/`slow_window`
  with chronological train/validation/holdout partitions. Holdout is
  sealed from candidate selection and evaluated exactly once for the
  selected candidate; every candidate, rejection, and failure is
  persisted and visible.
- Browse all of the above through an accessible, strict-TypeScript web
  dashboard that performs no financial calculation itself — every number
  displayed comes directly from the backend as a decimal string.

## Known v1 limitations

- **Single instrument only.** Multi-instrument backtest runs and
  optimizations are explicitly rejected.
- **One strategy kind.** Only `sma_crossover` exists — long-only, no short
  selling, no custom code or expressions, no other indicator.
- **No run/execute UI.** Backtest runs and their execution can only be
  created and triggered through the API (`POST /api/v1/backtest-runs`,
  `POST /api/v1/backtest-runs/{id}:execute`); the frontend dashboard
  (`/runs`) can list and inspect runs but does not yet expose a
  create/execute form. The same applies to optimizations, which the
  frontend *can* create and execute (`/optimizations/new`).
- **No charting.** All evidence is presented as structured data and
  tables; no client-side or server-side chart rendering exists.
- **8 fixed metrics.** `initial_equity`, `final_equity`, `total_return`,
  `annualized_return`, `max_drawdown`, `trade_count`, `win_rate`,
  `realized_pnl`, `exposure_time_ratio` — no Sharpe/Sortino/custom
  objective, and optimization objectives are restricted to this same set.
- **Optimization search is finite-grid only.** No random, Bayesian, or
  genetic search; no walk-forward rolling re-optimization; no
  cross-validation shuffle; no multi-objective scoring. Objective ranking
  is always "highest value wins" — there is no minimize direction, because
  every v1 metric is already oriented so a higher value is better.
- **No market-data provider integration.** Only manual, offline CSV
  import exists; no live or historical data feed is connected.
- **No authentication or multi-user support.** Anyone with network access
  to the API can perform every operation. This is a local single-user
  research tool, not a hosted service.
- **Local persistence only.** DuckDB is a single local file; there is no
  distributed execution, no concurrent-run scaling, and no managed backup.
- **No CI pipeline or hosted deployment.** Quality gates
  (`ruff`/`mypy`/`pytest`, `eslint`/`tsc`/`vitest`/`next build`) and Docker
  builds are run and documented per task, but no continuous-integration
  automation or production hosting exists in this repository.

## Verification evidence (TASK-013)

- Backend: `ruff format --check .`, `ruff check .`, `mypy .`, `pytest -q`
  — all clean, 280 tests passed.
- Frontend: `npm run format`, `npm run lint`, `npm run type-check`,
  `npm run test`, `npm run build` — all clean, 84 tests passed, 13 routes
  built.
- `docker compose build api web` — both images build successfully.
- Live end-to-end smoke test against the built Docker images: dataset
  import → instrument → instrument mapping → strategy creation → backtest
  run creation/execution → run summary/artifacts/reproducibility-manifest
  retrieval → optimization creation/execution (reached `completed`) — all
  succeeded via real HTTP calls. All 9 frontend routes (`/`, `/datasets`,
  `/datasets/import`, `/runs`, `/strategies`, `/strategies/new`,
  `/optimizations`, `/optimizations/new`, `/system`) returned `200` from
  the live web container pointed at the live API container.
