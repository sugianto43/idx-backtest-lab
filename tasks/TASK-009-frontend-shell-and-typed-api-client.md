# TASK-009 — Frontend shell and typed API client

## Objective

Create the Next.js/TypeScript frontend foundation: application shell, accessible route navigation, strict typed API client, and system-status page. It must consume only existing backend health/readiness contracts and make unavailable product workflows explicit.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/CODING_STANDARDS.md`, `docs/TDD.md`, `docs/API_CONVENTIONS.md`, `docs/FRONTEND_FOUNDATION_CONTRACT.md`, ADR-008, TASK-001, TASK-002, TASK-008, and this task.

## Dependencies

TASK-001 and TASK-002 must be complete and verified. TASK-008 is required only for the shared result-integrity language/UI state patterns; it does not require building result screens. Preserve current backend contracts; if an expected health/readiness contract differs, fix/document it only through its owning completed task/change policy.

## In scope

- Next.js app initialization, strict TypeScript, formatter/linter/type/test configuration, and development/container integration specified by TASK-001.
- Global layout/navigation/disclaimer and the routes in `FRONTEND_FOUNDATION_CONTRACT.md`.
- Central typed API client with health/readiness calls and normalized API errors.
- Reusable accessible loading, empty, warning, unavailable, and error state components.
- Component/client tests, accessibility-focused checks, and API-client contract tests with mocked responses.

## Out of scope

- Dataset import/list/detail workflow, run creation/results, strategy forms, charts, tables beyond small system-status displays, or any mutation except no-op/system reads.
- Financial calculations, decimal parsing into float, client-side metric derivation, or client-side reconstruction of warnings.
- Authentication, analytics, cookies beyond framework essentials, browser storage, external UI kits, global state libraries, and backend changes unrelated to a documented contract defect.

## Implementation requirements

- Use strict TypeScript; avoid `any` and unsafe assertions. Keep server/client boundary intentional and minimal.
- Organize shared layout/components separately from API transport/types. No component calls raw `fetch` for product API access.
- Validate the public API base URL at the API-client boundary. Do not hard-code development hostnames inside components.
- Normalize network, timeout, malformed-response, and documented API errors to one typed UI error model; retain correlation IDs.
- `/system` displays backend liveness/readiness with clear distinction between API unavailable, API live/database unavailable, and ready. Do not expose technical paths or stack traces.
- Placeholder routes must be useful but compact: state what future task owns the capability and provide no fake controls.
- Include the research disclaimer globally and in any screen that may later present results.

## Test plan

1. Routes render one page heading, landmark structure, keyboard-accessible navigation, current-page indication, and global disclaimer.
2. API client forms correct versioned URLs, validates configuration, parses successful health/readiness payloads, propagates correlation IDs, and normalizes all documented error cases.
3. Malformed/non-JSON/network/timeout responses render a safe error state without crashes or raw payload leakage.
4. Loading, unavailable, error, warning, and empty components are semantically distinguishable and screen-reader accessible.
5. Decimal-string test values remain strings through the UI client/view model; no financial computation exists in frontend code.
6. Responsive smoke tests or equivalent assertions show navigation/content remain usable on narrow width.
7. Formatting, linting, strict type check, unit/component tests, and a production build pass.

## Acceptance criteria

- Frontend architecture follows ADR-008 and the foundation contract.
- All initial routes, navigation, disclaimer, and system-status behavior work accessibly.
- A single typed API client owns API transport and preserves safe error/correlation behavior.
- The frontend neither invents unavailable capabilities nor performs financial calculation.
- Full frontend quality checks pass; task/project docs report only verified commands and facts.

## Definition of done and handoff

After all checks pass, update status documents and fill:

- Framework/tool versions and commands: Next.js 16.2.12 (App Router, Turbopack), React 19.2.4, strict TypeScript. No new runtime dependencies — `lib/api/` uses native `fetch`/`AbortController`/`URL`. `npm run format|lint|type-check|test|build` from `frontend/`.
- API base-URL configuration behavior: `NEXT_PUBLIC_API_BASE_URL` (see `frontend/.env.example`), validated in `lib/api/config.ts::resolveApiBaseUrl()` — must parse as an `http`/`https` URL or every API call short-circuits to a `config_error` `ApiResult` without attempting a network request. No hard-coded fallback host. Next.js inlines `NEXT_PUBLIC_*` at build time, so a production build needs rebuilding after a value change (`next dev` reads it live).
- Route/component inventory: `/` (landing), `/datasets`, `/runs` (both placeholder, owned by TASK-010), `/strategies` (placeholder, owned by TASK-011), `/system` (client component; liveness → readiness sequential check rendering loading/API-unavailable/database-unavailable/unexpected-error/ready). Shell: `app/layout.tsx` (skip link, `SiteNav`, single `<main>` landmark, `Disclaimer` footer). Reusable: `components/layout/{SiteNav,Disclaimer,PlaceholderRoute}.tsx`, `components/status/{LoadingState,EmptyState,WarningState,UnavailableState,ErrorState}.tsx`. API transport: `lib/api/{config,types,client,health}.ts`.
- Commands/tests and results: `npm run format` / `lint` / `type-check` all clean; `npm run test` → 27 passed across 8 files (API client normalization, base-URL validation, nav current-page marking, all 5 status components, `/system` state transitions, `/datasets` placeholder shape, disclaimer, landing heading). `npm run build` succeeds (5 static routes). `docker compose build web` succeeds; a standalone `docker run ... npm run dev` + `curl` smoke test confirmed the SSR shell (skip link, nav with `aria-current`, single `<h1>`, footer disclaimer) and the `/system` loading state render correctly.
- Accessibility/responsive verification: One `<h1>` per route (enforced by tests), landmark structure (`header`/`nav[aria-label="Primary"]`/`main`/`footer`) via SSR HTML inspection, `aria-current="page"` on the active nav link, a focus-visible skip link to `#main-content`, `role="status"` (polite) for loading/warning/unavailable, `role="alert"` for errors. Responsive behavior (`globals.css`: flex column body, `max-width` content columns, wrapping nav, no horizontal overflow) was verified by CSS review and browser resize, not an automated viewport test — jsdom does not perform layout, so no CSS media-query behavior can be asserted in Vitest.
- Deferred UI features/risks: No `EmptyState` consumer exists yet (reserved for TASK-010's dataset/run lists). `/system`'s "database unavailable" branch has only been exercised against the documented `dependency_unavailable` error code from `docs/API_CONVENTIONS.md`/TASK-002 — any future readiness failure code would currently fall through to the generic `unexpected_error` `ErrorState`, which is a safe default but not a distinct UI state. No dark-mode-specific accessibility contrast audit was run beyond the existing `prefers-color-scheme` CSS variables inherited from TASK-001.

## Next task boundary

TASK-010 implements dataset/run workflow views using typed endpoints and backend-produced data. It must reuse this API client/state system and must not reimplement backend financial logic.
