# Frontend

Next.js/TypeScript web application for idx-backtesting-lab. TASK-001
established the application shell and quality tooling. TASK-009 adds global
navigation/disclaimer chrome, placeholder routes for dataset/run/strategy
workflows, a `/system` connectivity page, a single typed API client
(`lib/api/`), and reusable accessible status components
(`components/status/`). No dataset, strategy, or run functionality exists
yet — that is TASK-010/TASK-011.

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
