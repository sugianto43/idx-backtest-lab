# Task Index

## Usage

Tasks will live in `tasks/TASK-###-short-name.md`. Before starting a task, read its dependency tasks and linked ADRs. Keep this index current as tasks are created, split, completed, or superseded.

## Planned sequence

| ID | Task | Status | Depends on |
| --- | --- | --- | --- |
| TASK-001 | Repository bootstrap and developer tooling | Completed | — |
| TASK-002 | Backend application skeleton and health API | Completed | TASK-001 |
| TASK-003 | DuckDB schema, migrations, and repository ports | Completed | TASK-001, TASK-002 |
| TASK-004 | Market-data ingestion, validation, and provenance | Completed | TASK-003 |
| TASK-005 | Instrument and corporate-action data model | Completed | TASK-003, TASK-004 |
| TASK-006 | Backtest domain model and configuration manifest | Completed | TASK-002, TASK-003, TASK-005 |
| TASK-007 | Backtrader engine adapter and deterministic smoke strategy | Completed | TASK-004, TASK-006 |
| TASK-008 | Run artifacts, metrics, and reproducibility audit trail | Completed | TASK-007 |
| TASK-009 | Frontend shell and typed API client | Completed | TASK-001, TASK-002 |
| TASK-010 | Dataset/run workflow dashboard | Completed | TASK-008, TASK-009 |
| TASK-011 | Strategy authoring and validation UX | Completed | TASK-006, TASK-009, TASK-010 |
| TASK-012 | Optimization framework with bias safeguards | Completed | TASK-008, TASK-011 |
| TASK-013 | End-to-end quality, documentation, and release readiness | Completed | TASK-001–TASK-012 |
| TASK-014 | Backtest run creation and execution UX | Completed | TASK-006, TASK-009, TASK-010, TASK-011 |
| TASK-015 | Continuous integration pipeline | Completed | TASK-001–TASK-014 |
| TASK-016 | Yahoo Finance market data import | Completed | TASK-004 |

## Task template

Every task must include: objective, context, dependencies, scope/allowed files, non-goals, requirements, acceptance criteria, test plan, definition of done, and handoff notes.
