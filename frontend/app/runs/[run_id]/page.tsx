"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { MetricValue } from "@/components/data/MetricValue";
import { PaginationControls } from "@/components/data/PaginationControls";
import { ProvenanceList } from "@/components/data/ProvenanceList";
import { ResponsiveTable } from "@/components/data/ResponsiveTable";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { UnavailableState } from "@/components/status/UnavailableState";
import { WarningState } from "@/components/status/WarningState";
import { formatDecimalString } from "@/lib/format/decimal";
import { executeRun, fetchRun, type BacktestRunResponse } from "@/lib/api/runs";
import {
  fetchReproducibilityManifest,
  fetchRunArtifacts,
  fetchRunEvents,
  fetchRunPortfolioSnapshots,
  fetchRunSummary,
  type EventType,
  type PaginatedEventsResponse,
  type PortfolioSnapshotsResponse,
  type ReproducibilityManifestResponse,
  type RunArtifactsResponse,
  type RunSummaryResponse,
} from "@/lib/api/run-artifacts";
import type { ApiError } from "@/lib/api/types";

const EVENT_TYPES: EventType[] = ["order", "fill", "position", "cash", "warning"];
const PAGE_SIZE = 20;

type Loadable<T> =
  | { kind: "loading" }
  | { kind: "error"; error: ApiError }
  | { kind: "not_found" }
  | { kind: "loaded"; data: T };

function useLoadable<T>(
  load: () => Promise<{ ok: true; data: T } | { ok: false; error: ApiError }>,
  deps: unknown[],
): Loadable<T> {
  const [state, setState] = useState<Loadable<T>>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    load().then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setState({ kind: "loaded", data: result.data });
      } else if (result.error.kind === "api_error" && result.error.code === "not_found") {
        setState({ kind: "not_found" });
      } else {
        setState({ kind: "error", error: result.error });
      }
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}

function downloadManifest(manifest: ReproducibilityManifestResponse) {
  const blob = new Blob([JSON.stringify(manifest.manifest, null, 2)], {
    type: manifest.content_type,
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = manifest.filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function RunDetailPage() {
  const params = useParams<{ run_id: string }>();
  const runId = params.run_id;

  const [reloadToken, setReloadToken] = useState(0);
  const [executing, setExecuting] = useState(false);
  const [executeError, setExecuteError] = useState<ApiError | null>(null);

  const run = useLoadable<BacktestRunResponse>(() => fetchRun(runId), [runId, reloadToken]);
  const summary = useLoadable<RunSummaryResponse>(
    () => fetchRunSummary(runId),
    [runId, reloadToken],
  );
  const artifacts = useLoadable<RunArtifactsResponse>(
    () => fetchRunArtifacts(runId),
    [runId, reloadToken],
  );
  const repro = useLoadable<ReproducibilityManifestResponse>(
    () => fetchReproducibilityManifest(runId),
    [runId, reloadToken],
  );

  async function handleExecute() {
    setExecuting(true);
    setExecuteError(null);
    const result = await executeRun(runId);
    setExecuting(false);
    if (!result.ok) {
      setExecuteError(result.error);
      return;
    }
    setReloadToken((token) => token + 1);
  }

  const [eventType, setEventType] = useState<EventType>("fill");
  const [eventOffset, setEventOffset] = useState(0);
  const events = useLoadable<PaginatedEventsResponse>(
    () => fetchRunEvents(runId, { type: eventType, limit: PAGE_SIZE, offset: eventOffset }),
    [runId, eventType, eventOffset],
  );

  const [snapshotOffset, setSnapshotOffset] = useState(0);
  const snapshots = useLoadable<PortfolioSnapshotsResponse>(
    () => fetchRunPortfolioSnapshots(runId, { limit: PAGE_SIZE, offset: snapshotOffset }),
    [runId, snapshotOffset],
  );

  if (run.kind === "loading") {
    return (
      <>
        <h1>Run</h1>
        <LoadingState label="Loading run…" />
      </>
    );
  }
  if (run.kind === "error" || run.kind === "not_found") {
    return (
      <>
        <h1>Run</h1>
        {run.kind === "not_found" ? (
          <UnavailableState message="This run does not exist." />
        ) : (
          <ErrorState error={run.error} />
        )}
      </>
    );
  }

  const runData = run.data;

  return (
    <>
      <h1>Run {runData.run_id}</h1>
      <Disclaimer />

      <section aria-labelledby="status-heading">
        <h2 id="status-heading">Status</h2>
        <p>
          Status: <strong>{runData.status}</strong>
          {summary.kind === "loaded" && summary.data.terminal_status
            ? ` (terminal: ${summary.data.terminal_status})`
            : null}
        </p>
        {runData.warning_count > 0 ? (
          <WarningState
            message={`${runData.warning_count} warning${runData.warning_count === 1 ? "" : "s"} were recorded during execution.`}
          />
        ) : (
          <p>No warnings recorded.</p>
        )}
        {runData.status === "created" && (
          <p>
            <button type="button" onClick={handleExecute} disabled={executing}>
              {executing ? "Executing…" : "Execute run"}
            </button>
          </p>
        )}
        {executing && <LoadingState label="Executing run…" />}
        {executeError && <ErrorState error={executeError} />}
      </section>

      <section aria-labelledby="provenance-heading">
        <h2 id="provenance-heading">Reproducibility and provenance</h2>
        {artifacts.kind === "loading" && <LoadingState label="Loading provenance…" />}
        {artifacts.kind === "not_found" && (
          <UnavailableState message="This run has not produced result artifacts yet. Execute it first." />
        )}
        {artifacts.kind === "error" && <ErrorState error={artifacts.error} />}
        {artifacts.kind === "loaded" && (
          <>
            <ProvenanceList
              items={[
                { label: "Dataset ID", value: runData.dataset_id },
                { label: "Strategy ID", value: runData.strategy_id },
                { label: "Strategy version", value: String(runData.strategy_version ?? "—") },
                { label: "Manifest checksum", value: runData.manifest_checksum },
                { label: "Artifact bundle checksum", value: artifacts.data.checksum },
                {
                  label: "Engine adapter",
                  value: String(artifacts.data.provenance.engine_adapter_name ?? "—"),
                },
              ]}
            />
            {repro.kind === "loaded" && (
              <p>
                <button type="button" onClick={() => downloadManifest(repro.data)}>
                  Download reproducibility manifest ({repro.data.filename})
                </button>
                <br />
                Contains the full run manifest, provenance, and checksums. Excludes raw market data,
                file paths, and credentials.
              </p>
            )}
            {repro.kind === "not_found" && (
              <UnavailableState message="No reproducibility manifest is available for this run yet." />
            )}
            {repro.kind === "error" && <ErrorState error={repro.error} />}
          </>
        )}
      </section>

      <section aria-labelledby="metrics-heading">
        <h2 id="metrics-heading">Metrics</h2>
        {summary.kind === "loading" && <LoadingState label="Loading metrics…" />}
        {summary.kind === "error" && <ErrorState error={summary.error} />}
        {summary.kind === "loaded" && summary.data.metrics.length === 0 && (
          <UnavailableState message="No metrics are available for this run yet." />
        )}
        {summary.kind === "loaded" && summary.data.metrics.length > 0 && (
          <dl>
            {summary.data.metrics.map((metric) => (
              <MetricValue
                key={metric.metric_key}
                label={metric.metric_key}
                metric={{ status: metric.status, value: metric.value, reason: metric.reason }}
              />
            ))}
          </dl>
        )}
      </section>

      <section aria-labelledby="events-heading">
        <h2 id="events-heading">Execution events</h2>
        <label htmlFor="event-type">Event type</label>
        <select
          id="event-type"
          value={eventType}
          onChange={(event) => {
            setEventType(event.target.value as EventType);
            setEventOffset(0);
          }}
        >
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        {events.kind === "loading" && <LoadingState label="Loading events…" />}
        {events.kind === "error" && <ErrorState error={events.error} />}
        {events.kind === "not_found" && (
          <UnavailableState message="No events are available for this run yet." />
        )}
        {events.kind === "loaded" && events.data.items.length === 0 && (
          <p>No {eventType} events.</p>
        )}
        {events.kind === "loaded" && events.data.items.length > 0 && (
          <>
            <ResponsiveTable caption={`${eventType} events`}>
              <thead>
                <tr>
                  {Object.keys(events.data.items[0]).map((key) => (
                    <th key={key} scope="col">
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {events.data.items.map((item, index) => (
                  <tr key={index}>
                    {Object.values(item).map((value, columnIndex) => (
                      <td key={columnIndex}>{value === null ? "—" : String(value)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </ResponsiveTable>
            <PaginationControls
              limit={PAGE_SIZE}
              offset={eventOffset}
              total={events.data.total}
              onPrevious={() => setEventOffset(Math.max(0, eventOffset - PAGE_SIZE))}
              onNext={() => setEventOffset(eventOffset + PAGE_SIZE)}
            />
          </>
        )}
      </section>

      <section aria-labelledby="snapshots-heading">
        <h2 id="snapshots-heading">Portfolio snapshots</h2>
        {snapshots.kind === "loading" && <LoadingState label="Loading snapshots…" />}
        {snapshots.kind === "error" && <ErrorState error={snapshots.error} />}
        {snapshots.kind === "not_found" && (
          <UnavailableState message="No portfolio snapshots are available for this run yet." />
        )}
        {snapshots.kind === "loaded" && snapshots.data.items.length === 0 && (
          <p>No portfolio snapshots.</p>
        )}
        {snapshots.kind === "loaded" && snapshots.data.items.length > 0 && (
          <>
            <ResponsiveTable caption="Portfolio snapshots">
              <thead>
                <tr>
                  <th scope="col">Sequence</th>
                  <th scope="col">Timestamp</th>
                  <th scope="col">Cash</th>
                  <th scope="col">Holdings value</th>
                  <th scope="col">Total equity</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.data.items.map((snapshot) => (
                  <tr key={snapshot.sequence}>
                    <td>{snapshot.sequence}</td>
                    <td>{snapshot.timestamp_utc}</td>
                    <td>{formatDecimalString(snapshot.cash)}</td>
                    <td>{formatDecimalString(snapshot.holdings_value)}</td>
                    <td>{formatDecimalString(snapshot.total_equity)}</td>
                    <td>{snapshot.status}</td>
                  </tr>
                ))}
              </tbody>
            </ResponsiveTable>
            <PaginationControls
              limit={PAGE_SIZE}
              offset={snapshotOffset}
              total={snapshots.data.total}
              onPrevious={() => setSnapshotOffset(Math.max(0, snapshotOffset - PAGE_SIZE))}
              onNext={() => setSnapshotOffset(snapshotOffset + PAGE_SIZE)}
            />
          </>
        )}
      </section>

      <section aria-labelledby="manifest-heading">
        <h2 id="manifest-heading">Full run manifest</h2>
        <pre className="id-value">{JSON.stringify(runData.manifest, null, 2)}</pre>
      </section>
    </>
  );
}
