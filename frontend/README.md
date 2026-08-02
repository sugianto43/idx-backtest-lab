# Frontend

Next.js/TypeScript web application for idx-backtesting-lab. TASK-001
established the application shell and quality tooling. TASK-009 adds global
navigation/disclaimer chrome, a `/system` connectivity page, a single typed
API client (`lib/api/`), and reusable accessible status components
(`components/status/`). TASK-010 adds the dataset import/list/detail and run
list/detail dashboard (`/datasets`, `/datasets/import`,
`/datasets/[dataset_id]`, `/runs`, `/runs/[run_id]`), reusable data-display
components (`components/data/`), and a precision-safe decimal display
utility (`lib/format/decimal.ts`). TASK-011 adds strategy authoring
(`/strategies`, `/strategies/new`, `/strategies/[strategy_id]/versions/[version]`)
and JSON-body POST support in `lib/api/client.ts`. TASK-012 adds the
optimization workflow (`/optimizations`, `/optimizations/new`,
`/optimizations/[optimization_id]`) for the backend's chronological
train/validation/holdout parameter optimizer. TASK-014 adds `/runs/new` and
an "Execute run" action on `/runs/{run_id}`, so backtest runs no longer
require a direct API call to create or execute.

## Prerequisites

- Node.js 22
- npm

## Local setup

```bash
cd frontend
npm install
cp .env.example .env.local
```

## Configuration

`NEXT_PUBLIC_API_BASE_URL` is the browser-safe base URL for the backend API
(e.g. `http://localhost:8000`). It is required — there is no hard-coded
fallback host. Because Next.js inlines `NEXT_PUBLIC_*` variables at build
time, a **production build must be rebuilt** if this value changes; `next
dev` re-reads it on each request, so local development works without a
rebuild. If it is missing or not a valid `http(s)` URL, every API call
resolves to a `config_error` and the affected UI shows a safe unavailable
state instead of guessing a host.

## Dataset/run dashboard

The dashboard reads only backend-provided values — decimal fields from the
API are always `string`s and are formatted for display with
`formatDecimalString()` (thousands-separator grouping on the string itself,
no `parseFloat`/`Number()` conversion, so arbitrarily long decimal precision
like `annualized_return` is never truncated). `MetricValue` and table cells
render `not_available` metrics with their backend-provided `reason` and
never substitute zero or blank. `WarningsList` always renders the full
warning list next to its count — warnings are never reachable only through
a collapsed-by-default control. Pagination is explicit Previous/Next
controls backed by the API's `limit`/`offset`; no route loads an entire
event/snapshot collection client-side. The reproducibility manifest
"download" button packages the already-fetched, backend-provided JSON
(filename/content-type as returned by the API) into a `Blob` — it never
regenerates or recomputes the manifest client-side.

## Strategy authoring

`/strategies/new` submits exactly the v1 `sma_crossover` contract payload.
`price_field` (`close`), `signal_time` (`bar_close`), and `long_only`
(`true`) are v1-fixed and never presented as user choices; `eligible_after_bars`
is derived from `slow_window` and shown read-only rather than being a
separate input. Window inputs are `text`/`inputMode="numeric"` validated
against `^[1-9]\d*$` — not `type="number"` — so decimal and scientific-notation
values (`2.5`, `1e3`) are rejected client-side rather than silently coerced.
Client checks are ergonomic only: the backend remains authoritative, and a
server rejection preserves every entered value for retry. `/strategies/{id}/versions/{version}`
renders the returned specification as read-only structured data (no inputs,
no buttons) and never claims a strategy is profitable, active, or executable.

## Optimization workflow

`/optimizations/new` submits an explicit finite `fast_windows`/`slow_windows`
grid, six chronological train/validation/holdout dates, and one predeclared
objective metric — the same 9 keys as the run-artifact contract. The
"candidate count" preview is pure combinatorics (counting `fast < slow`
pairs client-side) — presentational, not a financial calculation. On
`/optimizations/{id}`, the holdout section reads only the API's own
`holdout.sealed` flag (never re-derived from `status` client-side): while
sealed it renders a distinct `UnavailableState` instead of any holdout
field, and only shows holdout run ID/objective once the backend itself
reports the optimization `completed`. Rejected candidate pairs surface as an
always-visible warning banner, not a collapsed count. The candidates table
never requests more than one page at a time and never shows holdout data.

## Run the app

```bash
npm run dev
```

Open http://localhost:3000.

## Quality commands

Run from `frontend/`:

```bash
npm run format       # prettier check
npm run lint          # eslint
npm run type-check    # tsc --noEmit
npm run test           # vitest
npm run build           # production build
```

Auto-fix formatting with `npm run format:write`.

## Docker

From the repository root: `docker compose up web`. The container installs
dependencies from `package-lock.json`, serves the app on port 3000, and
`docker-compose.yml` sets `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
for it (the browser, not the container, makes the API calls, so this must
be a host-reachable URL, not the internal `api` service hostname).
