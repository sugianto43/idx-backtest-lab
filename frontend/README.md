# Frontend

Next.js/TypeScript web application for idx-backtesting-lab. TASK-001
established the application shell and quality tooling. TASK-009 adds global
navigation/disclaimer chrome, a `/system` connectivity page, a single typed
API client (`lib/api/`), and reusable accessible status components
(`components/status/`). TASK-010 adds the dataset import/list/detail and run
list/detail dashboard (`/datasets`, `/datasets/import`,
`/datasets/[dataset_id]`, `/runs`, `/runs/[run_id]`), reusable data-display
components (`components/data/`), and a precision-safe decimal display
utility (`lib/format/decimal.ts`). `/strategies` remains a placeholder —
that is TASK-011.

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
