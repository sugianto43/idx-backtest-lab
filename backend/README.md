# Backend Blueprint

Claude Code should create the backend during TASK-002 and later tasks, using the boundaries defined in `.claude/ARCHITECTURE_RULES.md` and `docs/TDD.md`.

The intended package responsibilities are:

- `api`: HTTP transport and contract validation only.
- `application`: use cases and ports.
- `domain`: framework-independent business rules.
- `infrastructure`: DuckDB, engine, filesystem, and provider adapters.

No backend source code, dependency configuration, or executable runtime is intentionally present yet.
