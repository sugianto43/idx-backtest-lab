# Prompt Library

Use these prompts as task starters. Replace bracketed text with concrete context. Always attach the relevant task file and follow `CLAUDE.md`.

## Implement a task

> Implement `[TASK-ID]`. First read `.claude/CLAUDE.md`, the task, linked ADRs, and relevant code/tests. Summarize the acceptance criteria and integrity risks before editing. Make the smallest coherent change, add/update tests, run the verification ladder, then report changed behavior, tests actually run, assumptions, and open risks. Do not modify files outside scope without explaining why.

## Investigate a defect

> Investigate `[symptom]` without changing behavior unless a safe, scoped fix is explicitly requested. Trace the issue from input to output, identify the earliest failing invariant or boundary, and give evidence. Pay special attention to time handling, adjustment status, missing data, fill timing, and rounding. Report root cause, impact, reproducer, and recommended fix.

## Review a change

> Review the current change against `.claude/AI_AGENT_CONSTITUTION.md`, architecture rules, task acceptance criteria, and tests. Prioritize correctness risks: look-ahead bias, nondeterminism, input provenance, silent fallbacks, money/rounding errors, API compatibility, and security. Return findings ordered by severity with file/line evidence; do not propose cosmetic-only findings.

## Design an ADR

> Draft an ADR for `[decision]`. Describe context, decision drivers, options, consequences, migration/reversibility, tests/validation, and unresolved risks. Do not present unverified vendor or data-provider claims as fact.

## Create a new task

> Create a narrowly scoped task for `[outcome]`, including objective, context, dependencies, allowed/forbidden files, requirements, acceptance criteria, test plan, definition of done, and handoff notes. Ensure it can be completed independently without hidden assumptions.
