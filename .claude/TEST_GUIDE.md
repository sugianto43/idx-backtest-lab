# Test Guide

## Testing goal

Tests must establish that a result is correct, deterministic, and honest about its assumptions—not merely that code executes.

## Test layers

| Layer | Proves | Examples |
| --- | --- | --- |
| Unit | Pure domain behavior | position sizing, fee rounding, indicator windows |
| Property | Invariants across generated cases | no negative cash when disallowed; chronological ordering |
| Repository | Persistence mapping and migration behavior | round-trip a run manifest; reject invalid schema |
| Contract | API schema and error stability | invalid config returns documented error code |
| Integration | Adapter interaction | fixture dataset produces expected normalized bars/artifacts |
| End-to-end | User workflow | import dataset, execute run, inspect results |

## Mandatory scenarios for simulation work

- Signal availability versus fill timing (no look-ahead).
- Session boundaries, holidays, time zones, and absent bars.
- Corporate-action and adjustment-policy behavior.
- Suspensions, zero volume, halted/delisted instruments, and missing prices.
- Fees, taxes, slippage, price limits, partial/rejected fills, and rounding.
- Identical input manifest/configuration produces identical artifacts.
- Invalid or incomplete data produces a visible rejection or warning, never a silent financial assumption.

## Fixtures and assertions

Use tiny, human-auditable fixtures with source/provenance metadata. Mark synthetic fixtures clearly and construct them to expose a single behavior. Assert externally meaningful outputs: manifests, orders/fills, balances, warnings, and stable error codes. Avoid snapshots that conceal the important calculation.

## Test quality

Tests must be isolated, deterministic, fast enough for local development, and independent of live market-data services. Freeze clocks/randomness when required and test interfaces at adapter boundaries.
