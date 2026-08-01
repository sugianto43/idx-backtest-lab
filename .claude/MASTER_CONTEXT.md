# Master Context

## Product

`idx-backtesting-lab` is a local-first, web-based research platform for designing, executing, comparing, and auditing backtests for Indonesia Stock Exchange (IDX) equities. It will combine a Python backend, a browser dashboard, DuckDB-backed research data, and a backtesting engine with a clean adapter boundary.

## Primary users

- Individual Indonesian equity researchers who need repeatable strategy experiments.
- Quant-minded analysts who need transparent assumptions and auditable run history.

## Product outcomes

- Import and validate lawful historical market data.
- Define strategies and execution assumptions explicitly.
- Run deterministic backtests without look-ahead bias.
- Inspect equity curves, orders, trades, metrics, and warnings.
- Compare runs with enough metadata to reproduce or challenge a result.

## Initial technology direction

| Area | Direction |
| --- | --- |
| API | Python + FastAPI |
| UI | Next.js + TypeScript |
| Data store | DuckDB for local analytical data and run artifacts |
| Backtesting | Backtrader behind an internal engine adapter |
| Deployment | Docker Compose for local development |

Technology choices remain provisional until recorded in ADRs. Implementations must not couple business logic directly to framework, database, or engine APIs.

## Core domain language

- **Dataset**: versioned market-data collection plus provenance and quality metadata.
- **Instrument**: an IDX-listed security identified by a stable internal ID and ticker history.
- **Bar**: OHLCV observation with exchange date/time, source, and adjustment status.
- **Strategy**: versioned rule set that produces signals from permitted historical inputs.
- **Backtest run**: immutable execution of one strategy version over one dataset/configuration.
- **Execution model**: rules converting signals to fills, including timing, commissions, taxes, slippage, liquidity, and price limits.
- **Artifact**: stored output of a run: orders, fills, trades, portfolio series, metrics, warnings, logs, and manifest.

## Baseline simulation assumptions

No assumption is implicit. At minimum, a run configuration must state its date range, universe, initial capital and currency, bar interval, signal/fill timing, corporate-action treatment, commission/tax/slippage models, and benchmark definition. Defaults must be visible in the UI and persisted in the manifest.

## Non-goals for the first release

- Live trading or order routing.
- Personalized investment recommendations.
- Claims of alpha or predictive accuracy.
- Multi-user brokerage custody or portfolio management.

## Delivery principles

Build vertical slices: a minimal but complete data-to-result workflow before advanced optimization, indicators, or visualization polish. Every layer must be testable in isolation and observable in an integrated run.
