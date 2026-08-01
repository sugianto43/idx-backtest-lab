# Run Artifact and Metric Contract

## Artifact bundle

After a terminal engine result, persist one immutable bundle with a positive `artifact_schema_version`, bundle checksum, creation timestamp, and these sections:

| Section | Required contents |
| --- | --- |
| `provenance` | run ID/manifest checksum, strategy ID/version/checksum, dataset ID/checksum, instrument resolution version, engine adapter/version, application version, artifact schema version. |
| `execution_events` | exact product-neutral orders, fills, positions, cash events, and warnings from TASK-007, preserving order/timestamps/rounding components. |
| `portfolio_snapshots` | chronological values: timestamp, cash, holdings market value, total equity, currency, valuation status/warnings. |
| `metrics` | named metric values/status/definition version and calculation inputs. |
| `audit` | creation time, deterministic execution metadata, warning count, terminal status/failure code, checksums, and safe correlation/run IDs. |

An artifact bundle is written only for a terminal run. Failed runs receive a failure artifact/audit record where available; no fabricated portfolio or metric data is written.

## Valuation policy v1

Portfolio valuation uses the declared dataset bars only. At each available bar close, value cash plus holdings marked at that bar’s close. No forward filling across absent bars, no external quote, FX conversion, corporate-action transformation, or inferred delisting value. If a holding cannot be valued under this rule, mark the snapshot/metric `not_available` with a warning; do not produce a misleading equity value.

## Metric definitions v1

Metric values are decimal strings or `null`, never binary floating point. Every record includes `status: available|not_available`, `definition_version: 1`, and a short safe reason when unavailable.

| Metric | Definition |
| --- | --- |
| `initial_equity` | Initial capital from the run manifest. |
| `final_equity` | Last available valid total-equity snapshot. |
| `total_return` | `(final_equity / initial_equity) - 1`; unavailable without valid endpoints. |
| `annualized_return` | `(final_equity / initial_equity)^(annualization_basis / elapsed_session_count) - 1`; unavailable if endpoints/nonzero elapsed sessions are absent. |
| `max_drawdown` | Minimum of `(equity_t / running_max_equity_t) - 1` over valid chronological snapshots. |
| `trade_count` | Count of completed round-trip trades under documented FIFO lot matching. |
| `win_rate` | Profitable completed FIFO-matched trades divided by `trade_count`; unavailable at zero trades. |
| `realized_pnl` | Sum of completed FIFO lot P&L, excluding costs only if costs are explicitly zero; otherwise include recorded fill components. |
| `exposure_time_ratio` | Sessions with a nonzero market-valued position divided by valid valuation sessions. |

`sharpe_ratio`, benchmark-relative metrics, volatility, tax-aware P&L, and unrealized P&L are not available in v1. Do not render zero in place of an unavailable metric.

## Reproducibility manifest

Exportable JSON contains all provenance checksums/versions, canonical run manifest, artifact checksum, schema/metric definition versions, event/snapshot counts, warnings, and the exact command/application/engine version metadata required to rerun. It excludes secrets, raw file paths, and raw input content unless explicitly exported through a separate safe workflow.

## Compatibility for comparison

Runs may be marked `comparable` only if they use the same artifact schema, metric definition version, currency, bar interval, annualization basis, valuation policy, and compatible dataset adjustment treatment. Otherwise comparison must return a reasoned incompatibility warning, not a numerical ranking.
