# TASK-017 — Visual design system and onboarding home page

## Objective

The user reported the app "doesn't look modern" and, on first load, gave no indication of what to do. Replace the bare-bones global styling with a cohesive, modern visual design system, and redesign `/` into a guided onboarding page (a numbered "getting started" flow plus quick links to every existing workflow) instead of two paragraphs of static text. Pure presentation and navigation-affordance work — no new API calls, no new backend behavior, no change to any existing route's data or logic.

## Required reading

Read `.claude/CLAUDE.md`, `docs/FRONTEND_FOUNDATION_CONTRACT.md` (accessibility/responsive requirements this must keep satisfying), TASK-009 (global shell), and this task.

## Dependencies

TASK-009 through TASK-014 (all frontend tasks) must be complete and verified (they are). This task only restyles and reorganizes what they built.

## In scope

- `app/globals.css`: a real design system — color/spacing/radius tokens (light + dark via `prefers-color-scheme`), styled buttons/inputs/selects/fieldsets/legends, card surfaces, a polished sticky header with a brand link, pill-style nav with a clear current-page state, restyled tables (header shading, row hover, contained border/radius), and richer warning/error/unavailable status treatments (tinted background, not just a colored left border) — all via CSS targeting existing semantic HTML, not per-page markup rewrites, so no existing component's DOM structure/test assertions change.
- `app/layout.tsx`: add a brand/home link in the header alongside the existing nav (small, additive change).
- `app/page.tsx`: replace the two static paragraphs with a short hero (what the tool is/does, disclaimer already lives in the footer) plus a numbered "Getting started" step list (Import a dataset → Create a strategy → Create a run → View results, and a mention of optimizations) linking directly to the relevant creation routes, plus a compact set of links to every list page for a returning user.
- Updating `app/page.test.tsx` for the new home page content (the existing single-`<h1>`/no-own-`<main>` assertions must still hold).

## Out of scope

- Any new API call, new route, new backend behavior, or change to any existing page's data-fetching logic.
- A component/design library, CSS-in-JS, or any new dependency — plain CSS only, consistent with every prior frontend task.
- Charting, animations beyond simple CSS transitions, or a full rebrand (logo/illustration assets).

## Test plan

1. Every existing frontend test still passes unmodified except `app/page.test.tsx`, which is updated for the new home page content while preserving its accessibility assertions (one `<h1>`, no page-owned `<main>`).
2. The home page's "Getting started" links resolve to the correct existing routes (`/datasets/import`, `/strategies/new`, `/runs/new`, `/optimizations/new`).
3. Lint/format/type-check/build all pass; no new dependency was added.
4. Manual/SSR verification that the header, nav current-page state, buttons, forms, and tables render the new styling across at least one representative page of each kind (a list page, a form page, a detail page).

## Acceptance criteria

- The app has a consistent, modern visual identity across every route without any route's underlying accessibility structure regressing.
- A first-time visitor on `/` can see, without scrolling past unrelated content, exactly what to do first.
- All quality checks pass; status/handoff documents record only verified facts.

## Definition of done and handoff

After verification, update project memory/index and record:

- Design tokens and restyled elements: `--color-bg/surface/border/text/text-muted/accent/warning/danger/unavailable`, `--radius-sm/md`, `--shadow-sm/md` (light + dark via `prefers-color-scheme`) in `app/globals.css`. Restyled via existing selectors only: sticky header with `.brand` + pill nav, `button`, `input`/`select`/`textarea`, `fieldset`/`legend`, `.card`/`.step-card`/`.link-grid`, `.responsive-table` (header shading, row hover, contained border), `.warning-state`/`.error-state`/`.unavailable-state` (tinted backgrounds), `dl`.
- Home page content and link targets: 4-step "Getting started" grid → `/datasets/import`, `/strategies/new`, `/runs/new`, `/optimizations/new`; link grid to `/datasets`, `/runs`, `/strategies`, `/optimizations`, `/system`.
- Commands/tests and results: `npm run format`/`lint`/`type-check` clean, `npm run test` → 92 passed across 23 files (all pre-existing tests unchanged except `app/page.test.tsx`, which gained 2 tests for the new onboarding links), `npm run build` succeeds (13 routes). `docker compose build web` succeeds; SSR `curl` checks against the rebuilt container confirmed the brand link, `aria-current="page"`, and new card/table classes render.

## Next task boundary

None specific — purely presentational; any future task continues to build on the same design tokens rather than introducing a new styling approach.
