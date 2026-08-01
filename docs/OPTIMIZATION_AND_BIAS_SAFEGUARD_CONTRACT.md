# Optimization and Bias Safeguard Contract

## Scope

V1 optimizes only `sma_crossover.fast_window` and `sma_crossover.slow_window` across explicit finite integer lists. The objective is one existing available v1 backend metric, chosen before execution. No custom expression, client-side calculation, random search, or parameter outside the strategy contract is permitted.

## Chronological partitions

Every optimization manifest declares non-overlapping dates:

```text
train:      [train_start, train_end]
validation: [validation_start, validation_end]
holdout:    [holdout_start, holdout_end]
```

They must satisfy `train_end < validation_start <= validation_end < holdout_start <= holdout_end`, use the same dataset/interval/universe/adjustment treatment/execution policy, and each contain enough valid bars for the largest candidate window plus a completed next-bar fill opportunity. Boundaries use eligible exchange/session bars, not guessed calendar sessions.

## Candidate evaluation

1. Canonically expand the declared grid in stable lexicographic order `(fast_window, slow_window)`.
2. Reject invalid pairs (`fast_window >= slow_window`) before execution and record them as rejected candidates.
3. For each valid candidate, derive a new immutable strategy/version/run manifest for train and validation only, preserving all non-parameter assumptions.
4. Execute and artifact each candidate through existing validated engine/artifact paths.
5. Rank candidates only by the predeclared validation objective. An unavailable objective cannot win.
6. Tie-break deterministically: highest objective value, then lower `slow_window`, then lower `fast_window`, then canonical candidate ID.
7. Evaluate the selected candidate once on holdout. The holdout result cannot alter selected parameters.

## Research safeguards

- Holdout is sealed during selection: candidate-level holdout metrics/events are unavailable until selection completes.
- The UI/API must disclose candidate count, rejected/failed count, partition dates, objective, tie-break, selection rule, and holdout-sealed status.
- Failed/unavailable candidates remain recorded and visible; no retry or exclusion occurs without a new optimization manifest.
- An optimization cannot reuse a completed holdout evaluation or be resumed with changed inputs. Create a new optimization ID.
- Display a research-only warning: selection on historical validation data may be overfit and does not predict future performance.

## Immutable optimization manifest

Contains schema version/checksum, base strategy/dataset/run-policy references, canonical parameter grid, partition dates, objective key/direction/definition version, deterministic enumeration/tie-break rules, created timestamp, and engine/application versions. Defaults are materialized before checksum.

## Immutable result bundle

Contains optimization ID/manifest checksum, each candidate’s parameters/status/run IDs/validation objective/status/warnings, rejection/failure reasons, selection decision/audit timeline, selected candidate, sealed holdout run/artifact/metric, aggregate warning count, and result checksum. It never contains a prediction or recommendation.
