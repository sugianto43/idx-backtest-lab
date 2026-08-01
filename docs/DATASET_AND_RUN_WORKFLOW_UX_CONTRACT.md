# Dataset and Run Workflow UX Contract

## Purpose

The dashboard helps a researcher inspect imported data and completed backtest evidence. It must make provenance, configuration, warnings, and unavailable values at least as visible as headline performance figures.

## Dataset workflow

### Dataset list (`/datasets`)

Show paginated dataset cards/table rows with name, dataset ID, source name, interval, coverage, adjustment policy, validation status, warning count, creation time, and a clear empty state. Status is text plus icon/color, never color alone. Filters may include validation status and interval only if the API supports them.

### Dataset detail (`/datasets/{dataset_id}`)

Show immutable provenance: source/license reference, checksum, timezone, adjustment policy, coverage, validation summary/events, row/instrument counts, and created timestamp. Display unresolved identifier/quality warnings prominently. Do not render raw files, filesystem paths, or bar charts in v1.

### Import (`/datasets/import`)

Use the TASK-004 import endpoint and exact CSV contract. The form must label every required provenance field, link to the CSV contract, show client-side structural validation only as convenience, and treat server validation as authoritative. Before submit, state that a new immutable dataset version will be created. On failure, preserve non-sensitive form inputs and show safe server errors/correlation ID. On success, route to the new dataset detail and show warnings.

## Run workflow

### Run list (`/runs`)

Show paginated run summaries with run ID, status, dataset/strategy reference, creation time, warning count, final-equity/total-return only when `available`, and a visible unavailable state otherwise. Never sort/rank by an unavailable value or infer a zero.

### Run detail (`/runs/{run_id}`)

Use progressive sections:

1. Status and warning banner.
2. Reproducibility/provenance summary (dataset, strategy, engine, checksums, manifest link/export).
3. Backend-provided metrics with definition status/reason.
4. Execution-event and portfolio-snapshot tables with stable pagination/filtering.
5. Full immutable manifest displayed as inspectable structured data.

No client-side recomputation. Charting is deferred; tables and textual summaries must be sufficient for audit.

## Error, warning, and loading behavior

Use foundation components from TASK-009. An unavailable artifact, failed run, or unavailable metric is not a generic error: preserve its backend-provided status/reason and recommend the safe next action. User-facing technical IDs must be copyable, but avoid exposing paths or stack traces.

## Responsive/accessibility criteria

Tables support a responsive alternative (stacked rows or horizontal scroll with accessible labels), keyboard focus, header associations, captions/summaries, and safe long-ID/checksum wrapping. Status changes use live regions without stealing focus.
