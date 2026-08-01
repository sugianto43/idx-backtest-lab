# Review Guide

## Review priority

Review for correctness and risk before style. A small code change can invalidate all research results if it changes information timing, data interpretation, or execution semantics.

## Required checklist

- Does the change meet the task's stated acceptance criteria?
- Can the result be reproduced from a versioned input manifest and deterministic configuration?
- Is every signal restricted to information available at its simulated decision time?
- Are data source, timezone, adjustment state, missing values, and corporate actions explicit?
- Are fills realistic for the declared execution model, with costs and rounding correctly applied?
- Does money avoid binary floating point, and are rounding rules deterministic?
- Are framework/database/engine details kept out of domain contracts?
- Are external inputs validated, database queries parameterized, and secrets protected?
- Do tests cover the changed behavior and meaningful boundary/negative cases?
- Are API/schema compatibility and documentation handled?

## Finding format

Each finding states severity, location, evidence, impact, and a concrete correction. Use severity only when it changes correctness, safety, reliability, or maintainability:

- **Critical**: can materially falsify results, leak sensitive data, or corrupt irreversible data.
- **High**: likely production failure or important incorrect behavior.
- **Medium**: meaningful edge case, contract weakness, or maintainability risk.
- **Low**: minor robustness concern with plausible future impact.

Do not report a finding without explaining the observed behavior and why it violates a requirement or invariant.
