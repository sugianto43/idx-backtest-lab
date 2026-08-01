# IDX Backtesting Lab

Local-first research tooling for transparent, reproducible backtests of Indonesia Stock Exchange (IDX) equities.

> Historical backtests are research artifacts, not investment advice and not a prediction of future performance.

## Current status

This repository is intentionally documentation-first. It contains the AI operating system, product/technical specifications, decision records, and task contracts required for Claude Code to build the application in controlled phases. It contains no application source code, dependency configuration, data, or credentials.

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/` | Backend build blueprint; source code is created by subsequent tasks |
| `frontend/` | Frontend build blueprint; source code is created by subsequent tasks |
| `docs/` | Product, technical, data, API, and decision documentation |
| `tasks/` | Executable work specifications |
| `.claude/` | Persistent operating context for AI-assisted work |

## How Claude Code should begin

1. Read `.claude/CLAUDE.md` and its required read order.
2. Read `docs/PRD.md`, `docs/TDD.md`, and `docs/adr/ADR-001-initial-technology-boundaries.md`.
3. Read `tasks/TASK-001-repository-bootstrap.md`.
4. Create only the files permitted by that task, verify its acceptance criteria, then update task status and project memory.

## AI-assisted development

Read `.claude/CLAUDE.md` before changing the repository. It defines required read order, research-integrity rules, verification expectations, and handoff format.

## License and data

No license has been selected yet. Do not add, redistribute, or commit market data until provider terms, provenance, and licensing have been formally decided.
