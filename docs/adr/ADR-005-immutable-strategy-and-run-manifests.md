# ADR-005: Immutable strategy specifications and run manifests

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

A backtest cannot be reproduced if strategy behavior, data selection, signal timing, execution assumptions, and metric settings are mutable or implicit. Existing run envelopes from TASK-003 need a formal versioned configuration contract before an engine adapter is introduced.

## Decision

Store strategy specifications and backtest run manifests as immutable, canonical JSON documents with explicit schema versions and content checksums. A run references an exact strategy-spec version and dataset version. Defaults that can affect a result are materialized in the persisted manifest; no runtime default is allowed to remain unstated.

The initial strategy form is a validated declarative specification for a limited built-in rule set. Arbitrary user code, plugins, and natural-language execution are out of scope.

## Consequences

- Runs become independently auditable and comparable.
- Schema evolution needs versioned parsers/migrations and contract fixtures.
- An engine adapter must accept only validated, fully materialized manifests.
- Optimization and user-authored code are deferred until safe isolation and evaluation policies are designed.

## Reversibility

Moderate. New schema versions can be added, but historic manifests must remain readable and never be rewritten in place.
