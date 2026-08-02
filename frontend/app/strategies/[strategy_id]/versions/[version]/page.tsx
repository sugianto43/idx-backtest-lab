"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ProvenanceList } from "@/components/data/ProvenanceList";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { UnavailableState } from "@/components/status/UnavailableState";
import { fetchStrategyVersion, type StrategySpecResponse } from "@/lib/api/strategies";
import type { ApiError } from "@/lib/api/types";

type State =
  | { kind: "loading" }
  | { kind: "not_found" }
  | { kind: "error"; error: ApiError }
  | { kind: "loaded"; data: StrategySpecResponse };

export default function StrategyVersionDetailPage() {
  const params = useParams<{ strategy_id: string; version: string }>();
  const strategyId = params.strategy_id;
  const version = Number(params.version);
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchStrategyVersion(strategyId, version).then((result) => {
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
  }, [strategyId, version]);

  if (state.kind === "loading") {
    return (
      <>
        <h1>Strategy version</h1>
        <LoadingState label="Loading strategy version…" />
      </>
    );
  }
  if (state.kind === "not_found") {
    return (
      <>
        <h1>Strategy version</h1>
        <UnavailableState message="This strategy version does not exist." />
      </>
    );
  }
  if (state.kind === "error") {
    return (
      <>
        <h1>Strategy version</h1>
        <ErrorState error={state.error} />
      </>
    );
  }

  const spec = state.data;

  return (
    <>
      <h1>
        {spec.name} (v{spec.version})
      </h1>
      <Disclaimer />
      <p>
        This is an immutable specification version — it cannot be edited. Creating a new version
        requires a new strategy. No historical performance is shown here; only a completed backtest
        run can demonstrate this strategy&apos;s behavior on specific data.
      </p>

      <section aria-labelledby="spec-heading">
        <h2 id="spec-heading">Specification</h2>
        <ProvenanceList
          items={[
            { label: "Strategy ID", value: spec.strategy_id },
            { label: "Version", value: String(spec.version) },
            { label: "Kind", value: spec.kind },
            { label: "Fast SMA window", value: String(spec.parameters.fast_window) },
            { label: "Slow SMA window", value: String(spec.parameters.slow_window) },
            { label: "Price field", value: spec.parameters.price_field },
            { label: "Checksum", value: spec.checksum },
            { label: "Created", value: spec.created_at_utc },
          ]}
        />
      </section>

      <section aria-labelledby="policy-heading">
        <h2 id="policy-heading">Signal policy</h2>
        <ul>
          <li>Signal timing: {spec.signal_policy.signal_time.replace("_", " ")}</li>
          <li>Eligible after bar: {spec.signal_policy.eligible_after_bars}</li>
          <li>Long-only: {spec.signal_policy.long_only ? "yes" : "no"}</li>
        </ul>
      </section>

      <section aria-labelledby="semantics-heading">
        <h2 id="semantics-heading">What this means</h2>
        <p>
          An upward crossover of the fast SMA above the slow SMA enters a long position; a downward
          crossover exits an open long position. Signals are evaluated at each bar&apos;s close, but
          any resulting order fills at the <strong>next bar&apos;s open</strong> in a backtest run —
          never at the signal bar&apos;s own close. This specification does not execute or evaluate
          anything by itself.
        </p>
      </section>
    </>
  );
}
