# Product Requirements Document

## Problem

IDX equity researchers often validate strategy ideas with spreadsheets or opaque tools. Those workflows make it difficult to determine which data, timing, corporate-action assumptions, and trading costs produced a result. `idx-backtesting-lab` provides a local-first, auditable alternative.

## Product statement

Enable a researcher to import lawful historical IDX data, configure a strategy and realistic execution assumptions, run a deterministic simulation, and inspect the complete evidence behind its results.

## Personas

- **Independent researcher:** explores a rule-based IDX equity hypothesis and needs results that can be repeated later.
- **Quant analyst:** compares experiments, challenges assumptions, and needs a durable audit trail.

## First-release user journeys

1. Create/import a dataset and see its provenance, coverage, quality warnings, and adjustment policy.
2. Select a universe, configure a predefined strategy, and specify capital, dates, signal/fill timing, and execution costs.
3. Run a backtest and view its immutable manifest, status, warnings, equity curve, trades, orders/fills, and documented metrics.
4. Compare compatible completed runs and understand differences in configuration and data.

## Functional requirements

| ID | Requirement |
| --- | --- |
| FR-01 | Ingest/import data only with recorded source, license reference, checksum/version, time range, and adjustment status. |
| FR-02 | Reject or visibly warn about invalid, incomplete, duplicated, out-of-order, or ambiguous market data. |
| FR-03 | Persist immutable, versioned strategy specifications and backtest configurations. |
| FR-04 | Persist immutable run manifests and result artifacts sufficient for repeatability. |
| FR-05 | Model order timing and execution assumptions explicitly; never hide defaults that change a financial result. |
| FR-06 | Show warnings prominently in result views and exports. |
| FR-07 | Provide documented, deterministic performance metrics with their formula and annualization basis. |
| FR-08 | Provide API errors with stable codes and actionable detail. |

## Non-functional requirements

- Local-first and usable without a hosted service for core workflows.
- Deterministic for the same engine, dataset, strategy, and run configuration.
- Testable without live market-data access.
- Accessible browser UI with explicit loading, empty, warning, and error states.
- No secrets or provider credentials in committed files, logs, or artifacts.

## Explicit exclusions

No live trading, brokerage connection, personalized recommendations, custody, portfolio management, or claims about future returns.

## Success criteria

The product is successful when a researcher can reproduce a prior result from its manifest, locate its source data and assumptions, and identify any data-quality/execution caveats without inspecting source code.
