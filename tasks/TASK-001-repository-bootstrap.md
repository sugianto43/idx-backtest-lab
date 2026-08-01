# TASK-001 — Repository bootstrap and developer tooling

## Objective

Establish a runnable, quality-gated monorepo foundation for the API and web application without implementing market-data or backtesting behavior.

## Context

Read `.claude/CLAUDE.md`, `.claude/MASTER_CONTEXT.md`, `docs/adr/ADR-001-initial-technology-boundaries.md`, and this task before changes.

## Dependencies

None.

## Scope

Allowed areas: root tooling/configuration, `backend/`, `frontend/`, `docs/adr/`, `.claude/PROJECT_MEMORY.md`, and this task/status index.

Forbidden: market-data provider integration, DuckDB schema, strategy semantics, backtesting execution, user authentication, or committing credentials/data.

## Requirements

- Provide Docker-based local API and web development services.
- Configure Python formatting, linting, strict type checking, and tests.
- Configure TypeScript strict checks, formatting, linting, and tests.
- Provide a dependency-free API liveness endpoint and a minimal accessible web landing page.
- Document startup, product boundary, and AI operating instructions.

## Acceptance criteria

- Root documentation explains the repository, local prerequisites, startup path, and quality commands.
- Docker Compose defines API and web development services with isolated dependency volumes and no committed secrets.
- The API serves `GET /health` with `{"status":"ok"}` after dependencies are installed.
- The web service renders an accessible landing page after dependencies are installed.
- Backend and frontend have formatter, linter, type-check, and test commands.
- No data credentials, market data, or unapproved simulation assumptions are present.

## Test plan

- Run Python lint, format check, type check, and unit test.
- Run TypeScript type check, lint, format check, and test command.
- Validate Docker Compose configuration.

## Definition of done

All acceptance criteria and test plan checks pass, task/index/project memory status is current, and no unrelated product capability was introduced.

## Handoff notes

The bootstrap does not make a data source or database schema decision. TASK-002 owns the next API slice; TASK-003 owns DuckDB persistence. When this task is complete, add the actual command names and verified results to the handoff.
