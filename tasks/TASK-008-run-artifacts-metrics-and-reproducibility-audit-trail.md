# TASK-008 — Run artifacts, metrics, and reproducibility audit trail

## Objective

Persist immutable, auditable artifacts from TASK-007 execution results; derive the v1 documented portfolio snapshots and metrics; and expose safe retrieval/export APIs. A visible result must be traceable to exact input/version/checksum evidence.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/AI_AGENT_CONSTITUTION.md`, `.claude/ARCHITECTURE_RULES.md`, `.claude/TEST_GUIDE.md`, `docs/BACKTEST_MANIFEST_CONTRACT.md`, `docs/ENGINE_EXECUTION_CONTRACT.md`, `docs/RESULT_ARTIFACT_AND_METRIC_CONTRACT.md`, ADR-005 through ADR-007, TASK-006, TASK-007, and this task.

## Dependencies

TASK-006 and TASK-007 must be completed and verified. Use their canonical manifests, deterministic `ExecutionResult`, lifecycle, engine metadata, and explicit v1 execution limitations. Do not change their timing or calculation semantics.

## In scope

- Append-only artifact persistence/migrations/repositories for execution events, portfolio snapshots, metric records, artifact bundle metadata, and reproducibility manifests.
- Pure deterministic projection/calculation from `ExecutionResult` plus exact run manifest/dataset snapshot.
- FIFO lot matching limited to the documented v1 trade-count/win-rate/realized-P&L definition.
- Safe API retrieval of run summary, artifact details, events, snapshots, metrics, and reproducibility-manifest export.
- Compatibility assessment for run comparison metadata; numerical comparison UI is deferred.

## Out of scope

- Altering engine order/fill/rounding/timing, adding execution assumptions, or mutating any source/run manifest.
- New metrics, Sharpe/volatility/benchmark performance, currency conversion, corporate-action transformation, forward-filled valuation, tax modeling beyond recorded events, or optimization.
- Frontend/dashboard work, charts, CSV/PDF reports, background jobs, retention/deletion policy, external analytics.

## Persistence design

Create an ordered migration with append-only tables (exact names may follow established conventions):

- `run_artifact_bundles`: bundle ID, run ID unique, schema version, checksum, terminal status, provenance JSON, event/snapshot/metric counts, creation timestamp.
- `run_order_events`, `run_fill_events`, `run_position_events`, `run_cash_events`, `run_warnings`: event identity/order, bundle/run ID, product-neutral fields, payload/checksum as needed.
- `portfolio_snapshots`: bundle/run ID, sequence/timestamp, cash, holdings value, total equity, currency, valuation status/reason.
- `run_metrics`: bundle/run ID, metric key, decimal/null value, availability status/reason, definition version, calculation-input JSON.
- `reproducibility_manifests`: bundle/run ID, canonical export JSON, checksum, created timestamp.

Require a unique artifact bundle per run, immutable inserts, chronological/sequence constraints, safe JSON handling, and foreign references to the exact run. Store monetary values as decimal-safe text/structured values, never float. Do not persist Backtrader objects or arbitrary pickles.

Artifact creation must be transactional as far as the storage supports: either a complete consistent terminal bundle exists, or it is marked/recorded safely as failed with no misleading partial metrics. Rerunning requires a new run ID, never replacement.

## Calculation requirements

- Project portfolios only from ordered TASK-007 events and declared dataset close prices according to the valuation policy.
- Keep calculation code framework/database/engine independent and testable with small hand-calculated fixtures.
- Apply deterministic FIFO lots per instrument for completed-trade metrics. Define entry/exit matching explicitly in code/docs and persist input components needed to audit a value.
- Include recorded commission/tax/slippage components in realized P&L when nonzero. V1 normally has zero components but must not assume this silently.
- Use manifest `annualization_basis` and session count exactly as documented. Do not substitute calendar days.
- Return `not_available` status/reason for insufficient/invalid valuation inputs; do not throw away warning evidence or coerce to zero.
- Compute/check bundle and reproducibility-manifest checksums using documented canonical serialization.

## API contract

Use standard error/correlation/pagination behavior. Add and contract-test:

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/v1/backtest-runs/{run_id}/summary` | Status, provenance summary, metric statuses/values, warning count; no huge event payload. |
| `GET` | `/api/v1/backtest-runs/{run_id}/artifacts` | Bundle metadata and paginated links/sections. |
| `GET` | `/api/v1/backtest-runs/{run_id}/events` | Paginated, stable-order execution event stream with type filter. |
| `GET` | `/api/v1/backtest-runs/{run_id}/portfolio-snapshots` | Paginated chronological valuation snapshots. |
| `GET` | `/api/v1/backtest-runs/{run_id}/metrics` | Metric records including definition/status/reason. |
| `GET` | `/api/v1/backtest-runs/{run_id}/reproducibility-manifest` | Safe JSON export of documented provenance/checksums only. |
| `GET` | `/api/v1/backtest-runs/{run_id}/comparison-compatibility?other_run_id=...` | Boolean compatibility plus specific reasons; no ranking. |

Return `404 not_found` for unknown runs and a clear stable status/error for runs without a terminal artifact. Never expose source files, database paths, internal exception details, or credentials.

## Test plan

Use tiny synthetic fixtures with manually derivable expected outputs. Test:

1. A completed `ExecutionResult` creates exactly one immutable consistent artifact bundle with correct checksums/provenance.
2. Event ordering, quantities, prices, zero/nonzero cost components, warnings, and terminal status survive persistence/retrieval exactly.
3. Portfolio snapshots value valid closes without forward fill; unvalued holdings generate warnings and unavailable metrics.
4. Each v1 metric matches hand calculation, including drawdown, annualization session basis, FIFO trade matching, costs, zero-trade handling, and decimal rounding.
5. Missing/invalid endpoints, insufficient sessions, invalid valuations, and no trades return `not_available` with reasons rather than zero/guesses.
6. Failed runs do not expose fabricated completed bundles/metrics.
7. Reproducibility manifest contains all required versions/checksums, is canonical/checksummed, and excludes secrets/paths/raw input.
8. Compatibility endpoint accepts only matching declared policies and reports each incompatibility reason.
9. Pagination, API errors, correlation IDs, migrations, immutability, static checks, and full offline suite pass.

## Acceptance criteria

- Artifact and metric behavior follows ADR-007 and the published contract exactly.
- Every persisted numeric result is traceable to events, snapshots, inputs, definitions, and checksum/version evidence.
- Unavailable/ambiguous valuation and metric conditions are visible, never silently filled or rendered as zero.
- Artifacts are append-only/immutable, safely retrievable, and no engine/framework types leak through APIs.
- Comparison compatibility protects against misleading cross-run ranking.
- All tests and quality gates pass; project memory/index/handoff contain verified facts only.

## Definition of done and handoff

After all checks pass, update status documents and complete:

- Migration/artifact schema version:
- Metric definition implementation notes:
- Valuation/FIFO edge-case policy:
- API endpoints and pagination:
- Commands/tests and results:
- Known limitations/deferred metrics:

## Next task boundary

TASK-009 creates the frontend shell and typed API client. TASK-010 consumes these retrieval endpoints in a dataset/run workflow dashboard. Neither task may recompute financial values in the browser.
