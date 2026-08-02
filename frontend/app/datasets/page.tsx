"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { PaginationControls } from "@/components/data/PaginationControls";
import { ResponsiveTable } from "@/components/data/ResponsiveTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { fetchDatasets, type DatasetListResponse } from "@/lib/api/datasets";
import type { ApiError } from "@/lib/api/types";

const LIMIT = 20;

type State =
  | { kind: "loading" }
  | { kind: "error"; error: ApiError }
  | { kind: "loaded"; data: DatasetListResponse };

export default function DatasetsPage() {
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchDatasets({ limit: LIMIT, offset }).then((result) => {
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
      <h1>Datasets</h1>
      <Disclaimer />
      <p>
        <Link href="/datasets/import">Import a new dataset</Link>
      </p>

      {state.kind === "loading" && <LoadingState label="Loading datasets…" />}
      {state.kind === "error" && <ErrorState error={state.error} />}
      {state.kind === "loaded" && state.data.items.length === 0 && (
        <EmptyState message="No datasets have been imported yet." />
      )}
      {state.kind === "loaded" && state.data.items.length > 0 && (
        <>
          <ResponsiveTable caption="Imported datasets">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Source</th>
                <th scope="col">Interval</th>
                <th scope="col">Coverage</th>
                <th scope="col">Adjustment policy</th>
                <th scope="col">Status</th>
                <th scope="col">Warnings</th>
                <th scope="col">Created</th>
              </tr>
            </thead>
            <tbody>
              {state.data.items.map((dataset) => (
                <tr key={dataset.dataset_id}>
                  <th scope="row">
                    <Link href={`/datasets/${dataset.dataset_id}`}>{dataset.name}</Link>
                  </th>
                  <td>{dataset.source_name}</td>
                  <td>{dataset.bar_interval}</td>
                  <td>
                    {dataset.coverage_start_date ?? "?"} – {dataset.coverage_end_date ?? "?"}
                  </td>
                  <td>{dataset.adjustment_policy}</td>
                  <td>{dataset.validation_status}</td>
                  <td>{dataset.warning_count}</td>
                  <td>{dataset.created_at_utc}</td>
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
