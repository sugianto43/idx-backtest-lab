"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { PaginationControls } from "@/components/data/PaginationControls";
import { ProvenanceList } from "@/components/data/ProvenanceList";
import { ResponsiveTable } from "@/components/data/ResponsiveTable";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { UnavailableState } from "@/components/status/UnavailableState";
import { WarningState } from "@/components/status/WarningState";
import { formatDecimalString } from "@/lib/format/decimal";
import {
  executeOptimization,
  fetchOptimization,
  fetchOptimizationCandidates,
  type OptimizationCandidatesResponse,
  type OptimizationDetail,
} from "@/lib/api/optimizations";
import type { ApiError } from "@/lib/api/types";

const PAGE_SIZE = 20;

type OptimizationState =
  | { kind: "loading" }
  | { kind: "not_found" }
  | { kind: "error"; error: ApiError }
  | { kind: "loaded"; data: OptimizationDetail };

export default function OptimizationDetailPage() {
  const params = useParams<{ optimization_id: string }>();
  const optimizationId = params.optimization_id;

  const [state, setState] = useState<OptimizationState>({ kind: "loading" });
  const [reloadToken, setReloadToken] = useState(0);
  const [executing, setExecuting] = useState(false);
  const [executeError, setExecuteError] = useState<ApiError | null>(null);

  const [offset, setOffset] = useState(0);
  const [candidatesState, setCandidatesState] = useState<
    | { kind: "loading" }
    | { kind: "error"; error: ApiError }
    | { kind: "loaded"; data: OptimizationCandidatesResponse }
  >({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchOptimization(optimizationId).then((result) => {
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
  }, [optimizationId, reloadToken]);

  useEffect(() => {
    let cancelled = false;
    fetchOptimizationCandidates(optimizationId, { limit: PAGE_SIZE, offset }).then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setCandidatesState({ kind: "loaded", data: result.data });
      } else {
        setCandidatesState({ kind: "error", error: result.error });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [optimizationId, offset, reloadToken]);

  async function handleExecute() {
    setExecuting(true);
    setExecuteError(null);
    const result = await executeOptimization(optimizationId);
    setExecuting(false);
    if (!result.ok) {
      setExecuteError(result.error);
      return;
    }
    setReloadToken((token) => token + 1);
  }

  if (state.kind === "loading") {
    return (
      <>
        <h1>Optimization</h1>
        <LoadingState label="Loading optimization…" />
      </>
    );
  }
  if (state.kind === "not_found") {
    return (
      <>
        <h1>Optimization</h1>
        <UnavailableState message="This optimization does not exist." />
      </>
    );
  }
  if (state.kind === "error") {
    return (
      <>
        <h1>Optimization</h1>
        <ErrorState error={state.error} />
      </>
    );
  }

  const optimization = state.data;

  return (
    <>
      <h1>{optimization.base_strategy_name}</h1>
      <Disclaimer />
      <p>
        Research evidence only. Selection on historical validation data may be overfit and does not
        predict future performance.
      </p>

      <section aria-labelledby="status-heading">
        <h2 id="status-heading">Status</h2>
        <p>
          Status: <strong>{optimization.status}</strong>
        </p>
        {optimization.rejected_count > 0 && (
          <WarningState
            message={`${optimization.rejected_count} candidate pair${optimization.rejected_count === 1 ? "" : "s"} were rejected (fast_window must be less than slow_window) and are recorded, not silently dropped.`}
          />
        )}
        {optimization.status === "created" && (
          <p>
            <button type="button" onClick={handleExecute} disabled={executing}>
              {executing ? "Executing…" : "Execute optimization"}
            </button>
          </p>
        )}
        {executing && <LoadingState label="Executing all candidates, selection, and holdout…" />}
        {executeError && <ErrorState error={executeError} />}
      </section>

      <section aria-labelledby="partitions-heading">
        <h2 id="partitions-heading">Chronological partitions</h2>
        <ProvenanceList
          items={[
            { label: "Train", value: `${optimization.train_start} – ${optimization.train_end}` },
            {
              label: "Validation",
              value: `${optimization.validation_start} – ${optimization.validation_end}`,
            },
            {
              label: "Holdout",
              value: `${optimization.holdout_start} – ${optimization.holdout_end}`,
            },
            { label: "Objective metric", value: optimization.objective_metric_key },
            { label: "Tie-break rule", value: optimization.tie_break_rule },
            { label: "Checksum", value: optimization.checksum },
          ]}
        />
      </section>

      <section aria-labelledby="selection-heading">
        <h2 id="selection-heading">Selection</h2>
        {optimization.selected_candidate_id === null ? (
          <UnavailableState message="No candidate has been selected yet." />
        ) : (
          <p>
            Selected candidate:{" "}
            <span className="id-value">{optimization.selected_candidate_id}</span>
            <br />
            Reason: {optimization.selection_reason}
          </p>
        )}
      </section>

      <section aria-labelledby="holdout-heading">
        <h2 id="holdout-heading">Holdout (sealed until completion)</h2>
        {optimization.holdout.sealed ? (
          <UnavailableState message="Holdout is sealed. It cannot influence candidate selection and is only revealed once the optimization reaches a terminal completed state." />
        ) : (
          <ProvenanceList
            items={[
              { label: "Holdout run ID", value: optimization.holdout.run_id },
              {
                label: "Objective status",
                value: optimization.holdout.objective_status,
              },
              {
                label: "Objective value",
                value:
                  optimization.holdout.objective_value !== null
                    ? formatDecimalString(optimization.holdout.objective_value)
                    : optimization.holdout.objective_reason,
              },
            ]}
          />
        )}
      </section>

      <section aria-labelledby="candidates-heading">
        <h2 id="candidates-heading">Candidates</h2>
        {candidatesState.kind === "loading" && <LoadingState label="Loading candidates…" />}
        {candidatesState.kind === "error" && <ErrorState error={candidatesState.error} />}
        {candidatesState.kind === "loaded" && (
          <>
            <ResponsiveTable caption="Candidates (train/validation only -- holdout is never shown here)">
              <thead>
                <tr>
                  <th scope="col">Fast</th>
                  <th scope="col">Slow</th>
                  <th scope="col">Status</th>
                  <th scope="col">Objective</th>
                  <th scope="col">Warnings</th>
                </tr>
              </thead>
              <tbody>
                {candidatesState.data.items.map((candidate) => (
                  <tr key={candidate.candidate_id}>
                    <td>{candidate.fast_window}</td>
                    <td>{candidate.slow_window}</td>
                    <td>
                      {candidate.status}
                      {candidate.rejection_reason ? ` (${candidate.rejection_reason})` : ""}
                    </td>
                    <td>
                      {candidate.objective_status === "available" &&
                      candidate.objective_value !== null
                        ? formatDecimalString(candidate.objective_value)
                        : candidate.objective_reason
                          ? `Not available (${candidate.objective_reason})`
                          : "—"}
                    </td>
                    <td>{candidate.warning_count}</td>
                  </tr>
                ))}
              </tbody>
            </ResponsiveTable>
            <PaginationControls
              limit={PAGE_SIZE}
              offset={offset}
              total={candidatesState.data.total}
              onPrevious={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              onNext={() => setOffset(offset + PAGE_SIZE)}
            />
          </>
        )}
      </section>

      <section aria-labelledby="manifest-heading">
        <h2 id="manifest-heading">Full immutable manifest</h2>
        <pre className="id-value">{JSON.stringify(optimization.manifest, null, 2)}</pre>
      </section>
    </>
  );
}
