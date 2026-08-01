# ADR-006: Backtrader engine adapter and deterministic execution

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

The product needs an executable backtest engine, but engine-specific classes, defaults, and ordering behavior must not become product contracts. Financial output must be reproducible from a validated run manifest and a fixed dataset snapshot.

## Decision

Use Backtrader behind an infrastructure adapter that accepts only product-neutral validated inputs and emits product-neutral execution events. The adapter has no persistence/API responsibility. It runs a deliberately limited v1 `sma_crossover` strategy with manifest-fixed `bar_close` signal generation and `next_bar_open` fill timing.

The adapter uses deterministic test clocks/inputs and explicit broker settings. Any Backtrader default affecting fills, cash, order status, or rounding must be materialized in adapter configuration or rejected as unsupported.

## Consequences

- Domain/API code does not expose Backtrader types.
- Engine integration is tested against tiny synthetic fixtures with event-level expected output.
- More strategy/execution behavior requires a contract/ADR update, not silent adapter options.
- TASK-008 owns durable artifact persistence and metric calculation; this task emits an in-memory product-neutral execution result.

## Reversibility

Moderate. The adapter port makes an engine replacement possible, but result semantics must remain contract-compatible.
