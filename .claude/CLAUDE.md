# idx-backtesting-lab — Operating Instructions

## Mission

Build a trustworthy, reproducible research and backtesting platform for Indonesian equities (IDX). The product must help users test hypotheses honestly; it must never imply that historical results guarantee future returns.

## Read order

Before changing code, read these files in order:

1. `.claude/MASTER_CONTEXT.md`
2. `.claude/PROJECT_MEMORY.md`
3. `.claude/ARCHITECTURE_RULES.md`
4. `.claude/CODING_STANDARDS.md`
5. The relevant task in `.claude/TASK_INDEX.md` and `tasks/` when present

Also read the closest applicable `README.md`, ADR, API contract, and test before editing. Treat this file as the repository-wide instruction source.

## Non-negotiable behavior

- Make the smallest coherent change that satisfies the active task.
- Do not invent market data, broker behavior, fees, corporate actions, or test results.
- Preserve reproducibility: version inputs, record configuration, pin dependencies, and make time zones explicit.
- Prevent look-ahead bias, survivorship bias, and accidental use of adjusted/unadjusted prices without an explicit policy.
- Keep financial calculations deterministic; use `Decimal` or integer minor units for money, never binary floating point for currency.
- Keep secrets out of source control. Update `.env.example` for every new required environment variable.
- Do not rewrite unrelated files, remove user changes, or add large dependencies without an ADR and approval.
- Stop and surface ambiguity when it materially affects financial correctness, data licensing, security, or user-facing behavior.

## Working loop

1. Restate the task internally and identify acceptance criteria.
2. Inspect the relevant implementation and tests.
3. Implement in small, cohesive commits/patches.
4. Run the narrowest relevant tests, then the required quality checks.
5. Update documentation, contracts, and `PROJECT_MEMORY.md` if a durable decision changed.
6. Report what changed, verification performed, and remaining risks.

## Definition of done

Work is done only when requirements and acceptance criteria are met, tests pass, errors are actionable, documentation reflects behavior, and no known integrity risk is hidden.

## Commands

Use project-defined commands from the root `README.md` or `Makefile` once they exist. Do not assume command names or toolchains before the repository bootstrap task establishes them.

## Communication

Be concise and evidence-based. Clearly distinguish facts, assumptions, and open questions. For a failed test or uncertainty, state the impact and the next safest action.
