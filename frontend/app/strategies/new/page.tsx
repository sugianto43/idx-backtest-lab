"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { createStrategy } from "@/lib/api/strategies";
import type { ApiError } from "@/lib/api/types";

const POSITIVE_INTEGER = /^[1-9]\d*$/;

function parsePositiveInteger(raw: string): number | null {
  if (!POSITIVE_INTEGER.test(raw.trim())) return null;
  const value = Number(raw.trim());
  return Number.isSafeInteger(value) ? value : null;
}

export default function NewStrategyPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [fastWindowRaw, setFastWindowRaw] = useState("");
  const [slowWindowRaw, setSlowWindowRaw] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const slowWindowPreview = parsePositiveInteger(slowWindowRaw);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setSubmitError(null);

    if (!name.trim()) {
      setClientError("Strategy name is required.");
      return;
    }
    const fastWindow = parsePositiveInteger(fastWindowRaw);
    const slowWindow = parsePositiveInteger(slowWindowRaw);
    if (fastWindow === null || slowWindow === null) {
      setClientError("Fast and slow windows must be positive whole numbers (no decimals).");
      return;
    }
    if (fastWindow >= slowWindow) {
      setClientError("The fast window must be smaller than the slow window.");
      return;
    }

    setSubmitting(true);
    const result = await createStrategy({ name, fastWindow, slowWindow });
    setSubmitting(false);

    if (!result.ok) {
      setSubmitError(result.error);
      return;
    }
    router.push(`/strategies/${result.data.strategy_id}/versions/${result.data.version}`);
  }

  return (
    <>
      <h1>Create a strategy</h1>
      <Disclaimer />
      <p>
        This creates a new, immutable strategy version — it cannot be edited afterward. Only the v1
        SMA crossover specification is supported.
      </p>
      <p>
        An upward crossover of the fast SMA above the slow SMA enters a long position; a downward
        crossover exits an open long position. This is a signal only — it does not guarantee an
        execution. When used in a backtest run, fills happen at the{" "}
        <strong>next bar&apos;s open</strong>, never at the signal bar&apos;s close.
      </p>

      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="name">Strategy name</label>
          <input
            id="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </div>

        <div>
          <label htmlFor="fast_window">Fast SMA window (bars)</label>
          <input
            id="fast_window"
            inputMode="numeric"
            pattern="[1-9][0-9]*"
            value={fastWindowRaw}
            onChange={(event) => setFastWindowRaw(event.target.value)}
            required
            aria-describedby="fast_window-help"
          />
          <p id="fast_window-help">A positive whole number, smaller than the slow window.</p>
        </div>

        <div>
          <label htmlFor="slow_window">Slow SMA window (bars)</label>
          <input
            id="slow_window"
            inputMode="numeric"
            pattern="[1-9][0-9]*"
            value={slowWindowRaw}
            onChange={(event) => setSlowWindowRaw(event.target.value)}
            required
            aria-describedby="slow_window-help"
          />
          <p id="slow_window-help">A positive whole number, larger than the fast window.</p>
        </div>

        <fieldset>
          <legend>Signal policy (fixed in v1, not user-configurable)</legend>
          <ul>
            <li>Signals are evaluated at each bar&apos;s close price.</li>
            <li>
              Eligible starting at bar{" "}
              {slowWindowPreview !== null ? slowWindowPreview : "<slow window>"} (the slow
              window&apos;s warm-up period).
            </li>
            <li>Long-only: no short selling.</li>
          </ul>
        </fieldset>

        {clientError ? <p role="alert">{clientError}</p> : null}

        <button type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create strategy"}
        </button>
      </form>

      {submitting && <LoadingState label="Creating strategy…" />}
      {submitError && <ErrorState error={submitError} />}
    </>
  );
}
