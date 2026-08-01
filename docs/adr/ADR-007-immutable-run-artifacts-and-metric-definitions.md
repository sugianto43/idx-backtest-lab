# ADR-007: Immutable run artifacts and metric definitions

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

Raw engine events alone are insufficient for research review. Results need durable, queryable artifacts and clearly defined metrics, while remaining traceable to exact inputs and engine behavior.

## Decision

Persist an append-only artifact bundle for each terminal run. The bundle references the exact run-manifest, strategy, dataset, and engine adapter checksums/versions, and includes raw execution events, portfolio snapshots, warnings, metrics, and a reproducibility manifest. Metrics use documented formulas and explicit annualization/risk-free assumptions. A completed artifact bundle is never recomputed or overwritten; reruns create new run IDs.

## Consequences

- A researcher can audit a visible number back to source inputs and execution events.
- Artifact schema/versioning and storage size/retention need disciplined migrations.
- Metrics must report `not_available` rather than silently substitute a formula/input.
- Results from different manifests/datasets are comparable only with explicit compatibility checks.

## Reversibility

Moderate. New artifact/metric schema versions are additive. Historic bundles stay readable under their recorded definition.
