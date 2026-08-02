"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { PaginationControls } from "@/components/data/PaginationControls";
import { ResponsiveTable } from "@/components/data/ResponsiveTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { fetchStrategies, type StrategySpecListResponse } from "@/lib/api/strategies";
import type { ApiError } from "@/lib/api/types";

const LIMIT = 20;

type State =
  | { kind: "loading" }
  | { kind: "error"; error: ApiError }
  | { kind: "loaded"; data: StrategySpecListResponse };

export default function StrategiesPage() {
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchStrategies({ limit: LIMIT, offset }).then((result) => {
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
      <h1>Strategies</h1>
      <Disclaimer />
      <p>
        <Link href="/strategies/new">Create a new strategy</Link>
      </p>

      {state.kind === "loading" && <LoadingState label="Loading strategies…" />}
      {state.kind === "error" && <ErrorState error={state.error} />}
      {state.kind === "loaded" && state.data.items.length === 0 && (
        <EmptyState message="No strategies have been created yet." />
      )}
      {state.kind === "loaded" && state.data.items.length > 0 && (
        <>
          <ResponsiveTable caption="Strategy specifications">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Kind</th>
                <th scope="col">Version</th>
                <th scope="col">Fast / slow window</th>
                <th scope="col">Created</th>
              </tr>
            </thead>
            <tbody>
              {state.data.items.map((strategy) => (
                <tr key={`${strategy.strategy_id}-${strategy.version}`}>
                  <th scope="row">
                    <Link href={`/strategies/${strategy.strategy_id}/versions/${strategy.version}`}>
                      {strategy.name}
                    </Link>
                  </th>
                  <td>{strategy.kind}</td>
                  <td>{strategy.version}</td>
                  <td>
                    {strategy.parameters.fast_window} / {strategy.parameters.slow_window}
                  </td>
                  <td>{strategy.created_at_utc}</td>
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
