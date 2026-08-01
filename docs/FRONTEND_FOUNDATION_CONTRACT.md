# Frontend Foundation Contract

## Goals

Create an accessible, local-first Next.js shell that establishes navigation, application chrome, typed API communication, environment validation, and reusable status states. It is a foundation, not a dataset/run dashboard.

## Initial routes

| Route | Purpose |
| --- | --- |
| `/` | Research-home landing page with product limitation/disclaimer. |
| `/datasets` | Placeholder route explaining dataset workflow arrives in TASK-010. |
| `/runs` | Placeholder route explaining run workflow arrives in TASK-010. |
| `/strategies` | Placeholder route explaining strategy workflow arrives in TASK-011. |
| `/system` | API connectivity/status view using only existing health/readiness contracts. |

Navigation must work by keyboard, identify the current page, and never imply unavailable features are complete.

## Typed API client

- One client module owns base-URL configuration, fetch behavior, response parsing, correlation-ID handling, timeout/abort behavior, and error normalization.
- Base URL uses a documented browser-safe environment variable. Missing/invalid configuration yields a clear development-safe UI state, not a fallback to an unknown host.
- Use the versioned API (`/api/v1`) for product calls. `/health` is permitted only for system liveness display.
- Define typed success/error models including API `error.code`, `message`, `details`, and `correlation_id`.
- Treat decimal string fields as strings/value-display types; do not parse them into JavaScript floating point for financial calculations.

## UI state contract

Every remote-data component has distinct accessible states: loading, empty, error, unavailable, warning, and success. An error view shows a safe message, stable code when available, and correlation ID for support; it does not display stack traces or raw response bodies.

Warnings from backend data/run responses remain visually distinct from errors and must not be hidden behind hover-only interaction.

## Accessibility and presentation

- Semantic HTML; a single visible page heading; landmarks; focus-visible controls; skip link; sufficient color contrast.
- Form controls have labels and inline error descriptions; status updates use appropriate live regions.
- Responsive layout at small and desktop widths; no horizontal overflow for normal content.
- Display a persistent research disclaimer in global shell/footer: historical simulations are not investment advice or future-performance predictions.

## Exclusions

No authentication, charting, file upload, strategy form, result tables, mutations, financial calculations, browser local persistence, or generic state-management framework is introduced in this task.
