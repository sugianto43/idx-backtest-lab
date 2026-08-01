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

- Framework/tool versions and commands:
- API base-URL configuration behavior:
- Route/component inventory:
- Commands/tests and results:
- Accessibility/responsive verification:
- Deferred UI features/risks:

## Next task boundary

TASK-010 implements dataset/run workflow views using typed endpoints and backend-produced data. It must reuse this API client/state system and must not reimplement backend financial logic.
