# Frontend

Next.js/TypeScript web application for idx-backtesting-lab. TASK-001 provides
only the application shell and quality tooling: a minimal accessible landing
page and no dataset, strategy, or run functionality.

## Prerequisites

- Node.js 22
- npm

## Local setup

```bash
cd frontend
npm install
```

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
dependencies from `package-lock.json` and serves the app on port 3000.
