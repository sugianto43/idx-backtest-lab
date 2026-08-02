"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { PaginationControls } from "@/components/data/PaginationControls";
import { ResponsiveTable } from "@/components/data/ResponsiveTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { fetchOptimizations, type OptimizationListResponse } from "@/lib/api/optimizations";
import type { ApiError } from "@/lib/api/types";

const LIMIT = 20;

type State =
  | { kind: "loading" }
  | { kind: "error"; error: ApiError }
  | { kind: "loaded"; data: OptimizationListResponse };

export default function OptimizationsPage() {
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchOptimizations({ limit: LIMIT, offset }).then((result) => {
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
      <h1>Optimizations</h1>
      <Disclaimer />
      <p>
        Research evidence only. Selection on historical validation data may be overfit and does not
        predict future performance.
      </p>
      <p>
        <Link href="/optimizations/new">Create a new optimization</Link>
      </p>

      {state.kind === "loading" && <LoadingState label="Loading optimizations…" />}
      {state.kind === "error" && <ErrorState error={state.error} />}
      {state.kind === "loaded" && state.data.items.length === 0 && (
        <EmptyState message="No optimizations have been created yet." />
      )}
      {state.kind === "loaded" && state.data.items.length > 0 && (
        <>
          <ResponsiveTable caption="Optimizations">
            <thead>
              <tr>
                <th scope="col">Strategy grid</th>
                <th scope="col">Status</th>
                <th scope="col">Objective</th>
                <th scope="col">Candidates</th>
                <th scope="col">Rejected</th>
                <th scope="col">Created</th>
              </tr>
            </thead>
            <tbody>
              {state.data.items.map((optimization) => (
                <tr key={optimization.optimization_id}>
                  <th scope="row">
                    <Link href={`/optimizations/${optimization.optimization_id}`}>
                      {optimization.base_strategy_name}
                    </Link>
                  </th>
                  <td>{optimization.status}</td>
                  <td>{optimization.objective_metric_key}</td>
                  <td>{optimization.candidate_count}</td>
                  <td>{optimization.rejected_count}</td>
                  <td>{optimization.created_at_utc}</td>
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
