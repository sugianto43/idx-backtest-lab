# TASK-002 — Backend application skeleton and health API

## Objective

Create the first runnable backend slice: a Python/FastAPI application with clean layer boundaries, a dependency-free health endpoint, stable error handling, and verified developer quality gates. This task creates platform scaffolding only; it does not create a market-data, database, strategy, or backtest feature.

## Required reading

Read, in order:

1. `.claude/CLAUDE.md`
2. `.claude/MASTER_CONTEXT.md`
3. `.claude/ARCHITECTURE_RULES.md`
4. `.claude/CODING_STANDARDS.md`
5. `docs/PRD.md`
6. `docs/TDD.md`
7. `docs/API_CONVENTIONS.md`
8. `docs/adr/ADR-001-initial-technology-boundaries.md`
9. `tasks/TASK-001-repository-bootstrap.md`
10. This task

## Dependencies

`TASK-001` must be completed and its documented quality commands must pass. If its actual project structure differs from assumptions below, preserve its established conventions and document the small adaptation in the handoff.

## Scope

### Allowed files

- `backend/**`
- Root runtime/tooling files created by TASK-001, only when required to add backend commands/dependencies
- `docs/API_CONVENTIONS.md` for verified implementation details only
- `.claude/PROJECT_MEMORY.md`
- `.claude/TASK_INDEX.md`
- This task's handoff/status section

### Forbidden work

- DuckDB schema, migrations, repositories, or direct SQL.
- Market-data provider, credentials, ingestion, sample market data, or corporate-action behavior.
- Backtrader or any execution-engine integration.
- Strategy configuration, portfolio logic, performance metrics, or financial calculations.
- Authentication/authorization, user accounts, external deployment, or frontend feature work.
- New cross-cutting dependencies unless indispensable and justified in an ADR.

## Technical requirements

### Application structure

Create a package layout that makes these boundaries visible even if some directories only contain package markers/documentation initially:

```text
backend/
  app/
    api/
      routes/
      schemas/
      errors.py
    application/
    domain/
    infrastructure/
    main.py
  tests/
```

`main.py` composes the FastAPI application and route registration. API routes must not contain domain logic, storage calls, or business calculations. Do not create fake repositories or placeholder domain entities merely to fill packages.

### Endpoints

Implement exactly these initial endpoints:

| Method | Path | Purpose | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | Dependency-free process liveness | `200 {"status":"ok"}` |
| `GET` | `/api/v1/health` | Versioned API readiness boundary | `200 {"status":"ok","service":"idx-backtesting-lab-api","version":"<package version>"}` |

Both endpoints must be deterministic, require no database/network access, and carry no business semantics. Do not present the versioned endpoint as proof that data sources or engine dependencies are ready.

### Error behavior

Install a single, documented error-mapping mechanism for future application errors. It must emit the envelope defined by `docs/API_CONVENTIONS.md`, include a generated or propagated `correlation_id`, and avoid stack traces in responses. For this task:

- Unknown routes return a JSON `404` response using the same envelope.
- Unhandled server errors return a JSON `500` response using a non-sensitive generic message and correlation ID; detailed context may be logged locally.
- Invalid request payloads return a JSON `422` response using the envelope and validation details safe for clients.

Choose stable lower-snake-case error codes, at least: `not_found`, `validation_error`, and `internal_error`. Document only behavior actually implemented.

### Configuration and observability

- Load runtime settings from environment variables through a typed configuration boundary.
- Define only settings needed by this task: application environment, log level, host, port, and application version if not sourced from package metadata.
- Never log secrets; do not add data-provider settings in this task.
- Configure structured or consistently formatted logs with timestamp, level, message, and correlation ID where request-scoped.
- Add middleware that accepts a valid incoming correlation ID or generates one, returns it in a response header, and makes it available to logs/error handling.

### Dependencies and quality tools

- Use a supported Python version selected by TASK-001, FastAPI, an ASGI server, and test client dependencies.
- Use the established formatter, linter, strict type checker, and test runner from TASK-001.
- Pin version ranges consistently with bootstrap conventions; do not introduce a database, data-science, or engine package.
- Provide a single documented backend command or command group for format check, lint, type check, and tests.

## Test plan

At minimum, create tests proving:

1. `GET /health` returns the exact documented liveness payload and `200`.
2. `GET /api/v1/health` returns `200` with non-empty service/version fields.
3. A request receives a correlation-ID response header; a valid supplied ID is preserved if that is the chosen policy.
4. An unknown route returns envelope-shaped JSON with `not_found`, `404`, and a correlation ID.
5. A validation failure on a deliberately added test-only/contract route or direct exception-handler test returns the documented safe `validation_error` envelope. Do not add a public business endpoint solely to exercise this test if handler tests suffice.
6. A simulated unexpected exception maps to a safe `internal_error` envelope without an exception message or stack trace.
7. The application imports and starts without database, network, market-data, or engine dependencies.

Use a test client and deterministic tests. Do not require Docker to run unit tests; Docker smoke verification may be additional evidence.

## Acceptance criteria

- The backend follows the API/application/domain/infrastructure boundary described in `docs/TDD.md`.
- Both documented health endpoints meet their exact response contracts.
- Error/validation/not-found responses use the documented envelope, stable codes, and correlation IDs.
- Configuration and request logging are typed, non-secret, and testable.
- Static checks, formatter check, strict type check, and all backend tests pass.
- API documentation only claims verified behavior.
- No persistence, market-data, strategy, or execution behavior is introduced.

## Definition of done

The task is complete only after the acceptance criteria and test plan pass. Update `PROJECT_MEMORY.md` with actual package/tooling facts, mark TASK-002 completed in `TASK_INDEX.md`, and append concise handoff notes to this file including exact commands run and their result. If a test cannot run, do not mark the task complete.

## Handoff notes

- Changes:
  - Package layout: `app/{api/{routes,schemas,errors.py,middleware.py},application,domain,infrastructure,main.py}`. `application`/`domain` are empty package markers only — no use cases exist yet.
  - `app/main.py` exposes `create_app()` (composition factory: settings → logging → FastAPI app → middleware → exception handlers → routers) and a module-level `app = create_app()` for `uvicorn app.main:app`.
  - `GET /health` (unversioned, dependency-free) → `{"status":"ok"}`. `GET /api/v1/health` → `{"status":"ok","service":"idx-backtesting-lab-api","version":"<Settings.version>"}`.
  - `app/infrastructure/settings.py`: `Settings` (pydantic-settings, env prefix `APP_`, `.env` support) with `environment`, `log_level`, `host`, `port`, `version` (default `0.1.0`); `get_settings()` is `lru_cache`d. `.env.example` documents all keys.
  - `app/infrastructure/correlation.py`: `ContextVar`-backed correlation ID get/set/generate. `app/infrastructure/logging.py`: `configure_logging(settings)` installs one `StreamHandler` with a formatter including timestamp/level/logger/correlation ID/message.
  - `app/api/middleware.py`: `CorrelationIdMiddleware` reads `X-Correlation-Id` if present and non-empty, else generates a uuid4 hex; always echoes it in the response header and makes it available to logs/error handlers via the contextvar.
  - `app/api/errors.py`: `ErrorBody`/`ErrorResponse` models matching `docs/API_CONVENTIONS.md` exactly; `AppError`/`NotFoundError` domain-safe exception types; `register_exception_handlers(app)` wires handlers for `StarletteHTTPException` (404 → `not_found`; other statuses → `http_error`), `RequestValidationError` (422 → `validation_error`, field-level `loc`/`message` details only), `AppError` (uses its own code/status/message), and the base `Exception` (500 → `internal_error`, full traceback logged server-side only, never returned to the client).
- Commands/tests run (from `backend/` with `.venv` active):
  - `ruff format --check .` → passed, 20 files already formatted.
  - `ruff check .` → passed, all checks passed (added `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls = ["fastapi.Depends", "fastapi.Query"]` to `pyproject.toml` so FastAPI's `Depends(...)` default-argument idiom doesn't trip B008).
  - `mypy` (strict) → passed, no issues in 19 source files.
  - `pytest -q` → passed, 7 passed (liveness payload, versioned health service/version, generated + preserved correlation ID header, 404/`not_found` envelope, 422/`validation_error` envelope with details, 500/`internal_error` envelope with no leaked exception text).
  - `docker compose build api` → image built successfully; standalone `docker run` smoke test confirmed `/health`, `/api/v1/health`, and an unknown route's `not_found` envelope all respond correctly inside the container.
- Results: all above commands passed with no known failures.
- Assumptions/adaptations:
  - Added `pydantic-settings==2.14.2` as a new direct runtime dependency (not present in TASK-001) to implement the typed configuration boundary; pinned in `requirements.txt`.
  - Correlation ID and structured-logging primitives live in `app/infrastructure/` (contextvar + logging filter); `app/api/middleware.py` depends on that infrastructure module to set the value per request. This is a pragmatic exception to strict inward-only dependency direction for a pure cross-cutting observability concern (not a business rule, repository, or engine adapter) — no domain/application code depends on it.
  - `422` uses `status.HTTP_422_UNPROCESSABLE_CONTENT` (the current non-deprecated Starlette/FastAPI constant name; same numeric value `422` as the contract requires) to avoid a `StarletteDeprecationWarning`.
  - The 500/`internal_error` test uses `TestClient(..., raise_server_exceptions=False)` because Starlette's `ServerErrorMiddleware` re-raises the original exception after invoking the registered handler by design (so real ASGI servers can log it) — this only affects the test harness, not runtime HTTP behavior, which already returns the safe envelope (verified via the container smoke test's `curl` output).
- Risks/follow-up:
  - No dedicated `/api/v1/ready` (database) endpoint yet — that's TASK-003 scope.
  - `application`/`domain` packages remain empty; first real use case arrives with TASK-003's repository ports.

## Next task boundary

TASK-003 introduces DuckDB schema initialization, migration/versioning, and repository ports. TASK-002 must leave that work as unimplemented interfaces or absent code; it must not create speculative database models.
