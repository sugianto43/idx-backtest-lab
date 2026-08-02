"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { PaginationControls } from "@/components/data/PaginationControls";
import { ResponsiveTable } from "@/components/data/ResponsiveTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { formatDecimalString } from "@/lib/format/decimal";
import { fetchRuns, type BacktestRunListResponse } from "@/lib/api/runs";
import type { ApiError, MetricValue } from "@/lib/api/types";

const LIMIT = 20;

type State =
  | { kind: "loading" }
  | { kind: "error"; error: ApiError }
  | { kind: "loaded"; data: BacktestRunListResponse };

function cellFor(metric: MetricValue): string {
  if (metric.status !== "available" || metric.value === null) {
    const suffix = metric.reason ? ` (${metric.reason})` : "";
    return `Not available${suffix}`;
  }
  return formatDecimalString(metric.value);
}

export default function RunsPage() {
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchRuns({ limit: LIMIT, offset }).then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setState({ kind: "loaded", data: result.data });
      } else {
        setState({ kind: "error", error: result.error });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [offset]);

  return (
    <>
      <h1>Runs</h1>
      <Disclaimer />

      {state.kind === "loading" && <LoadingState label="Loading runs…" />}
      {state.kind === "error" && <ErrorState error={state.error} />}
      {state.kind === "loaded" && state.data.items.length === 0 && (
        <EmptyState message="No backtest runs exist yet." />
      )}
      {state.kind === "loaded" && state.data.items.length > 0 && (
        <>
          <ResponsiveTable caption="Backtest runs">
            <thead>
              <tr>
                <th scope="col">Run</th>
                <th scope="col">Status</th>
                <th scope="col">Dataset</th>
                <th scope="col">Strategy</th>
                <th scope="col">Created</th>
                <th scope="col">Warnings</th>
                <th scope="col">Final equity</th>
                <th scope="col">Total return</th>
              </tr>
            </thead>
            <tbody>
              {state.data.items.map((run) => (
                <tr key={run.run_id}>
                  <th scope="row">
                    <Link href={`/runs/${run.run_id}`} className="id-value">
                      {run.run_id}
                    </Link>
                  </th>
                  <td>{run.status}</td>
                  <td className="id-value">{run.dataset_id}</td>
                  <td className="id-value">{run.strategy_id ?? "—"}</td>
                  <td>{run.created_at_utc}</td>
                  <td>{run.warning_count}</td>
                  <td>{cellFor(run.final_equity)}</td>
                  <td>{cellFor(run.total_return)}</td>
                </tr>
              ))}
            </tbody>
          </ResponsiveTable>
          <PaginationControls
            limit={LIMIT}
            offset={offset}
            total={state.data.total}
            onPrevious={() => setOffset(Math.max(0, offset - LIMIT))}
            onNext={() => setOffset(offset + LIMIT)}
          />
        </>
      )}
    </>
  );
}
