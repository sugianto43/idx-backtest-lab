# Development Workflow

## Before implementation

1. Locate the active task in `TASK_INDEX.md` or `tasks/`.
2. Read its dependencies and acceptance criteria.
3. Inspect related code, contracts, tests, and ADRs.
4. Identify financial/data integrity assumptions and unknowns.
5. Propose an ADR or ask for direction if the task crosses an ADR trigger.

## During implementation

1. Work in a narrow vertical slice.
2. Establish or update a failing test where practical, then implement the smallest correct change.
3. Keep transport/framework/engine details at adapter boundaries.
4. Make errors explicit; attach relevant run/dataset IDs in logs and responses.
5. Avoid unrelated formatting churn and refactors.

## Verification ladder

Run the strongest relevant checks available, from narrow to broad:

1. Formatter and static analysis for edited files.
2. Focused unit tests.
3. Module/package test suite.
4. Contract/integration tests for touched boundaries.
5. End-to-end smoke test for a user-visible workflow.

If a check cannot run, state why and what remains unverified. Do not claim validation that was not run.

## Documentation and handoff

Update task status, API docs, examples, ADRs, and `PROJECT_MEMORY.md` as appropriate. Handoff must include changed behavior, files/areas affected, tests executed and outcome, intentional assumptions, and follow-up risks.

## Git hygiene

Keep commits focused and reviewable. Do not commit secrets, generated caches, private data, oversized binaries, or unrelated local edits. Do not overwrite work you did not create.
