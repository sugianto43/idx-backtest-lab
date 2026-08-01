# ADR-008: Typed frontend and API boundary

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

The browser must present research workflows clearly without duplicating backend financial logic or becoming tightly coupled to undocumented response shapes.

## Decision

Use a strict TypeScript Next.js frontend with a single typed API client boundary. API request/response schemas are represented as TypeScript types derived from, or contract-tested against, the documented API. Browser components consume view models and never compute backtest metrics, fills, portfolio values, or assumptions.

## Consequences

- API changes surface through compile/test failures rather than silent UI breakage.
- UI can format a backend-provided decimal safely for display but cannot recalculate it.
- Error/correlation information can be presented consistently.
- State management remains local/server-component oriented until a concrete workflow needs a broader solution.

## Reversibility

High. The API client isolates component code from a later transport/query-library change.
