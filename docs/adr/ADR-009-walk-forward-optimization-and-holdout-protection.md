# ADR-009: Walk-forward optimization and holdout protection

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Parameter search can easily overfit historical data. A generic optimizer that sees all data or hides failed candidates would create misleading research results.

## Decision

The first optimizer supports only a declared finite grid over the existing SMA-crossover parameters, evaluated with chronological train/validation/holdout partitions. Holdout data is sealed from candidate selection and is evaluated once for the selected candidate. Every attempted candidate, failure, warning, partition, objective definition, seed/order, engine/data/manifest version, and selection decision is persisted immutably.

## Consequences

- Optimization is slower and more constrained, but auditable.
- No automatic parameter suggestion, random search, Bayesian search, cross-validation shuffle, or repeated holdout peeking is allowed in v1.
- The system can report an optimization result but must label it research-only, not predictive evidence.
- A new optimization run is required for every changed dataset/strategy/grid/partition/objective.

## Reversibility

Moderate. New search algorithms require an ADR, immutable result schema version, and bias-analysis test suite.
