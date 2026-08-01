# Debug Guide

## First principles

Debug from evidence, not intuition. Preserve the failing input, configuration, logs, and environment/version information before changing code. Never alter source data or silently retry a financial run to make a symptom disappear.

## Triage sequence

1. Capture the exact symptom, expected outcome, run/dataset IDs, timestamps, and reproducible command or UI path.
2. Classify the boundary: input/ingestion, normalization, domain calculation, engine adapter, persistence, API, or UI.
3. Reproduce with the smallest deterministic fixture.
4. Trace provenance and timing: raw bar → normalized bar → signal → order → fill → portfolio/metric.
5. Check invariants and inspect structured logs using the correlation/run ID.
6. Form one falsifiable hypothesis at a time; add a regression test before or alongside the fix.
7. Verify the fix narrowly, then run the relevant regression suite.

## Backtest-specific diagnostic questions

- Which data was known when the signal was generated?
- Were timestamps localized/converted correctly and sessions ordered correctly?
- Are bars raw or adjusted, and does that match the strategy and execution policy?
- Did an unavailable price, zero volume, halt, limit, or corporate action change fill behavior?
- Which fee/tax/slippage values and rounding policy were applied?
- Did any default or fallback enter the manifest, warning list, or logs?

## Bug report minimum

Record environment/version, concise reproduction, input fixture or safe reference, expected and actual behavior, logs/stack trace, affected run IDs, severity, and any suspected data-integrity impact. If historical output may be invalid, mark affected artifacts as suspect until revalidated.
