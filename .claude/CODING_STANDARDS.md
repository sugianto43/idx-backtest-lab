# Coding Standards

## General

- Optimize for readability, explicitness, and testability.
- Use names that express domain intent; avoid unexplained abbreviations.
- Keep functions focused and side effects at boundaries.
- Validate external input once at the boundary; represent validated concepts with typed domain values.
- Never catch broad exceptions merely to continue. Preserve causal context and expose actionable errors.
- Avoid speculative abstractions and premature configuration.

## Python backend

- Use modern Python type hints throughout public functions and domain/application boundaries.
- Prefer immutable models/value objects for run configuration and artifacts.
- Use Pydantic only at configuration/API boundaries; do not make all domain code framework-bound.
- Use `Decimal` for monetary amounts and document precision/rounding; use timezone-aware `datetime` only.
- Follow formatter, linter, type checker, and test configuration established by bootstrap. Add tests with `pytest` conventions once adopted.
- Separate pure calculations from I/O so bias-sensitive behavior can be tested deterministically.

## TypeScript frontend

- Enable strict TypeScript; no untyped `any` in production code.
- Keep API clients typed from explicit contracts; do not duplicate server-side formulas in UI components.
- Favor accessible semantic HTML, keyboard operation, readable empty/error states, and clear presentation of assumptions/warnings.
- Keep components small; isolate data fetching and visualization transformations from presentational components.

## Database and APIs

- Parameterize every query. Never assemble SQL from untrusted strings.
- Use migrations or versioned schema initialization; never mutate an existing user database implicitly without a migration path.
- Define request, response, and error schemas. Error responses must include stable machine-readable codes.
- Paginate unbounded collection endpoints and validate limits.

## Tests and docs

- Test behavior, not internal implementation details.
- Use fixtures with clear provenance; synthetic market data must be labeled synthetic.
- Include edge cases: empty ranges, missing sessions, split/dividend events, zero volume, suspended instruments, and rejected orders as applicable.
- Add comments only for non-obvious rationale. Update docs when interfaces or assumptions change.
