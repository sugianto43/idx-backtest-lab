# TASK-021 — Picker-based creation UX for runs and optimizations

## Objective

Replace the free-text ID-copy-paste convention on `/runs/new` and `/optimizations/new` with dropdown pickers populated from the actual API, per the user's request that creating a run/optimization take "just a click" after choosing from available options. `/strategies/new` already became picker-based in TASK-019/TASK-020 (kind selector + dynamic fields); this task covers the remaining two creation forms.

## Required reading

Read `.claude/CLAUDE.md`, TASK-010 (established the original ID-copy-paste convention and why), TASK-014, TASK-012, and this task.

## Dependencies

TASK-010/TASK-011/TASK-012/TASK-014 (existing list/creation pages) must be complete (they are).

## In scope

- `backend/app/api/routes/instruments.py`: new `GET /api/v1/datasets/{dataset_id}/instrument-mappings` (404 for an unknown dataset), reusing the existing `list_for_dataset` repository method that already existed but had no route. `backend/app/api/schemas/instruments.py`: new `DatasetMappingListResponse`.
- `frontend/lib/api/instruments.ts` (new): `fetchDatasetInstrumentMappings(datasetId)`.
- `frontend/app/runs/new/page.tsx`: replaces the Strategy ID/Strategy version/Dataset ID/Instrument ID text inputs with three selects — Strategy (one option per existing strategy version, `"name (vN)"`), Dataset (one option per dataset), Instrument (populated only after a dataset is chosen, from that dataset's instrument mappings; disabled until then).
- `frontend/app/optimizations/new/page.tsx`: same Dataset/Instrument select pattern (no strategy picker — an optimization creates its own strategy versions per candidate).
- Tests: backend API tests for the new list-mappings endpoint (success + 404); frontend tests for both forms covering picker loading states, the dataset-gates-instrument dependency, and the submitted payload shape.

## Out of scope

- Any picker for `/strategies/new`'s own fields — already done in TASK-019/TASK-020.
- A UI for creating instrument mappings (still API-only) — out of scope; the picker only *reads* existing mappings.
- Pagination within the pickers — a single page of up to 100 items is fetched, matching this product's local, single-user scale (documented, not silently truncated without indication).

## Test plan

1. Backend: `ruff format --check`, `ruff check`, `mypy`, `pytest -q` all clean; new endpoint tests cover success and unknown-dataset 404.
2. Frontend: `npm run format`/`lint`/`type-check`/`test`/`build` all clean; new tests cover picker population, the dataset→instrument dependency, and exact submitted payloads.
3. Manual: create a run and an optimization through the browser using only dropdowns, no copy-pasted IDs.

## Acceptance criteria

- No required identifier field on `/runs/new` or `/optimizations/new` is a free-text input the user must copy from another page.
- The instrument picker only ever offers instruments actually mapped to the selected dataset.
- All quality checks pass.

## Definition of done and handoff

After verification, update `.claude/PROJECT_MEMORY.md` and `.claude/TASK_INDEX.md` recording: the new list-mappings endpoint and why it existed at the repository layer but not as a route, the picker pattern (dataset-gates-instrument), and command/test results.

## Next task boundary

None specific — this closes out the user's original multi-part request (CSV-import removal, professional strategy kinds, custom combinations, one-click creation UX).
