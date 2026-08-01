# Claude Code Build Plan

## Execution protocol

For each task, Claude Code must read the task, its dependencies, `.claude/CLAUDE.md`, relevant ADRs, and relevant sections of `docs/`. It then implements only the stated scope, runs the task test plan, updates the task index/memory, and reports evidence plus open risks.

## Phase sequence

| Phase | Task(s) | Deliverable gate |
| --- | --- | --- |
| 2 | TASK-001 | Runnable repository/tooling skeleton, no business behavior |
| 3 | TASK-002–003 | Typed API skeleton and versioned local persistence boundary |
| 4 | TASK-004–005 | Provenanced/validated market-data and instrument model |
| 5 | TASK-006–008 | Reproducible backtest configuration, engine adapter, artifacts/metrics |
| 6 | TASK-009–011 | Browser workflow for datasets, runs, and strategy authoring |
| 7 | TASK-012–013 | Bias-aware optimization, full quality pass, release documentation |

## Required gates

1. No task begins while a dependency is incomplete or an ADR-critical decision is unresolved.
2. No market-data provider is integrated until licensing/provenance requirements are recorded.
3. No backtest result is presented without a persisted manifest and visible assumptions/warnings.
4. No UI calculation duplicates a backend financial calculation.
5. No release readiness claim without end-to-end fixture-based validation.

## Initial Claude Code prompt

> Read `.claude/CLAUDE.md`, `docs/PRD.md`, `docs/TDD.md`, `docs/DATA_GOVERNANCE.md`, `docs/API_CONVENTIONS.md`, `docs/adr/ADR-001-initial-technology-boundaries.md`, and `tasks/TASK-001-repository-bootstrap.md`. Implement TASK-001 only. Do not introduce market-data behavior or make unrecorded product decisions. Run every available verification item from the task and update `.claude/PROJECT_MEMORY.md` and `.claude/TASK_INDEX.md` only with verified facts.

## TASK-002 Claude Code prompt

> Confirm TASK-001 is completed with passing documented verification. Then read `.claude/CLAUDE.md`, `docs/TDD.md`, `docs/API_CONVENTIONS.md`, and `tasks/TASK-002-backend-application-skeleton.md`. Implement TASK-002 only. Keep all financial, data, database, and execution behavior out of scope. Verify the exact endpoint and error contracts, record only verified facts in project memory, and do not mark the task complete if any mandatory quality check cannot run.

## TASK-003 Claude Code prompt

> Confirm TASK-001 and TASK-002 are completed with passing documented verification. Then read `docs/adr/ADR-002-local-persistence-and-schema-evolution.md` and `tasks/TASK-003-duckdb-schema-migrations-and-repository-ports.md` in full. Implement TASK-003 only. Keep market-data ingestion, bar storage, strategy content, and backtest execution out of scope. Prove migration safety and repository behavior with temporary offline databases, then update status documents only with verified facts.

## TASK-004 Claude Code prompt

> Confirm TASK-001 through TASK-003 are completed with passing documented verification. Read `docs/adr/ADR-003-provider-neutral-local-csv-ingestion.md`, `docs/CSV_INGESTION_CONTRACT.md`, and `tasks/TASK-004-market-data-ingestion-validation-and-provenance.md` in full. Implement TASK-004 only. Use synthetic offline fixtures; do not integrate a provider, use real market data, infer adjustment semantics, or accept partial malformed imports. Verify provenance, immutability, cleanup, and all error/warning paths before updating task status.

## TASK-005 Claude Code prompt

> Confirm TASK-001 through TASK-004 are completed with passing documented verification. Read `docs/adr/ADR-004-effective-dated-instruments-and-corporate-actions.md`, `docs/INSTRUMENT_AND_CORPORATE_ACTION_CONTRACT.md`, and `tasks/TASK-005-instrument-and-corporate-action-data-model.md`. Implement TASK-005 only. Preserve raw dataset identifiers and bars; do not auto-match tickers or calculate any adjustment, cashflow, or tradability effect. Verify effective dates, conflicts, immutability, provenance, and error paths offline before updating status documents.

## TASK-006 Claude Code prompt

> Confirm required predecessor tasks are completed with passing documented verification. Read `docs/adr/ADR-005-immutable-strategy-and-run-manifests.md`, `docs/BACKTEST_MANIFEST_CONTRACT.md`, and `tasks/TASK-006-backtest-domain-model-and-configuration-manifest.md`. Implement TASK-006 only. Materialize every v1 assumption before persistence/checksum. Do not invoke an engine, compute indicators, generate orders/fills, or return performance metrics. Prove validation, canonicalization, immutability, and dependency resolution offline before changing task status.

## TASK-007 Claude Code prompt

> Confirm TASK-004 and TASK-006 are completed with passing documented verification. Read `docs/adr/ADR-006-backtrader-engine-adapter-and-deterministic-execution.md`, `docs/ENGINE_EXECUTION_CONTRACT.md`, and `tasks/TASK-007-backtrader-engine-adapter-and-deterministic-smoke-strategy.md`. Implement TASK-007 only. Keep Backtrader inside infrastructure, use a hand-auditable synthetic fixture, and prove close-signal/next-open-fill timing. Do not persist artifacts or calculate metrics; report all v1 execution limitations explicitly.

## TASK-008 Claude Code prompt

> Confirm TASK-006 and TASK-007 are completed with passing documented verification. Read `docs/adr/ADR-007-immutable-run-artifacts-and-metric-definitions.md`, `docs/RESULT_ARTIFACT_AND_METRIC_CONTRACT.md`, and `tasks/TASK-008-run-artifacts-metrics-and-reproducibility-audit-trail.md`. Implement TASK-008 only. Calculate solely from immutable product-neutral events and declared bars; make unavailable values explicit, persist one immutable bundle per run, and prove every metric with hand-auditable offline fixtures. Do not add UI, charts, or new execution semantics.

## TASK-009 Claude Code prompt

> Confirm TASK-001 and TASK-002 are completed with passing documented verification. Read `docs/adr/ADR-008-typed-frontend-api-boundary.md`, `docs/FRONTEND_FOUNDATION_CONTRACT.md`, and `tasks/TASK-009-frontend-shell-and-typed-api-client.md`. Implement TASK-009 only. Use a single strict typed API client, accessible status components, and honest placeholder routes. Do not add product workflow screens, API mutations, charts, financial calculations, or browser persistence. Run all frontend quality/build checks before updating status documents.

## TASK-010 Claude Code prompt

> Confirm TASK-004, TASK-008, and TASK-009 are completed with passing documented verification. Read `docs/DATASET_AND_RUN_WORKFLOW_UX_CONTRACT.md` and `tasks/TASK-010-dataset-run-workflow-dashboard.md` in full. Implement TASK-010 only. Consume typed backend data exactly, show provenance/warnings/unavailable states prominently, and keep all financial computation on the backend. Test import failures, failed/no-artifact runs, pagination, keyboard accessibility, and responsive tables before updating status documents.

## TASK-011 Claude Code prompt

> Confirm TASK-006, TASK-009, and TASK-010 are completed with passing documented verification. Read `docs/STRATEGY_AUTHORING_UX_CONTRACT.md` and `tasks/TASK-011-strategy-authoring-and-validation-ux.md` in full. Implement TASK-011 only. Author the exact declarative strategy v1 schema, use backend-authoritative validation, and make timing/long-only constraints plain. Do not add custom code, strategy preview, backtest triggering, or any performance claim/calculation. Run full frontend verification before updating status documents.

## TASK-012 Claude Code prompt

> Confirm TASK-008 and TASK-011 are completed with passing documented verification. Read `docs/adr/ADR-009-walk-forward-optimization-and-holdout-protection.md`, `docs/OPTIMIZATION_AND_BIAS_SAFEGUARD_CONTRACT.md`, and `tasks/TASK-012-optimization-framework-with-bias-safeguards.md` in full. Implement TASK-012 only. Use a finite canonical grid, chronological partitions, validation-only selection, and a single sealed holdout run. Persist all candidates/failures and keep all financial ranking/calculation on the backend. Prove holdout isolation with offline fixtures before updating status documents.
