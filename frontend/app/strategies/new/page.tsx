"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import {
  createStrategy,
  STRATEGY_KINDS,
  strategyKindConfig,
  type StrategyKind,
} from "@/lib/api/strategies";
import type { ApiError } from "@/lib/api/types";

const POSITIVE_INTEGER = /^[1-9]\d*$/;

function parsePositiveInteger(raw: string): number | null {
  if (!POSITIVE_INTEGER.test(raw.trim())) return null;
  const value = Number(raw.trim());
  return Number.isSafeInteger(value) ? value : null;
}

function defaultFieldValues(kind: StrategyKind): Record<string, string> {
  const config = strategyKindConfig(kind);
  const values: Record<string, string> = {};
  config?.fields.forEach((field) => {
    values[field.key] = String(field.defaultValue);
  });
  return values;
}

export default function NewStrategyPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [kind, setKind] = useState<StrategyKind>("sma_crossover");
  const [fieldValues, setFieldValues] = useState<Record<string, string>>(
    defaultFieldValues("sma_crossover"),
  );
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const config = strategyKindConfig(kind)!;

  const parsedPreviewParameters: Record<string, number> = {};
  for (const field of config.fields) {
    parsedPreviewParameters[field.key] = parsePositiveInteger(fieldValues[field.key] ?? "") ?? 0;
  }
  const eligibleAfterBarsPreview = config.requiredWarmupBars(parsedPreviewParameters);

  function handleKindChange(nextKind: StrategyKind) {
    setKind(nextKind);
    setFieldValues(defaultFieldValues(nextKind));
    setClientError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setSubmitError(null);

    if (!name.trim()) {
      setClientError("Strategy name is required.");
      return;
    }

    const parameters: Record<string, number> = {};
    for (const field of config.fields) {
      const parsed = parsePositiveInteger(fieldValues[field.key] ?? "");
      if (parsed === null) {
        setClientError(`${field.label} must be a positive whole number (no decimals).`);
        return;
      }
      parameters[field.key] = parsed;
    }
    if (kind === "sma_crossover" && parameters.fast_window >= parameters.slow_window) {
      setClientError("The fast window must be smaller than the slow window.");
      return;
    }
    if (
      kind === "rsi_threshold" &&
      parameters.oversold_threshold >= parameters.overbought_threshold
    ) {
      setClientError("The oversold threshold must be smaller than the overbought threshold.");
      return;
    }
    if (kind === "macd_crossover" && parameters.fast_period >= parameters.slow_period) {
      setClientError("The fast period must be smaller than the slow period.");
      return;
    }

    setSubmitting(true);
    const result = await createStrategy({
      name,
      kind,
      parameters,
      eligibleAfterBars: config.requiredWarmupBars(parameters),
    });
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
        This creates a new, immutable strategy version — it cannot be edited afterward. Pick a
        strategy kind and set its parameters below.
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
          <label htmlFor="kind">Strategy kind</label>
          <select
            id="kind"
            value={kind}
            onChange={(event) => handleKindChange(event.target.value as StrategyKind)}
          >
            {STRATEGY_KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
          <p id="kind-help">{config.description}</p>
        </div>

        <fieldset>
          <legend>{config.label} parameters</legend>
          {config.fields.map((field) => (
            <div key={field.key}>
              <label htmlFor={field.key}>{field.label}</label>
              <input
                id={field.key}
                inputMode="numeric"
                pattern="[1-9][0-9]*"
                value={fieldValues[field.key] ?? ""}
                onChange={(event) =>
                  setFieldValues({ ...fieldValues, [field.key]: event.target.value })
                }
                required
                aria-describedby={`${field.key}-help`}
              />
              <p id={`${field.key}-help`}>{field.help}</p>
            </div>
          ))}
        </fieldset>

        <fieldset>
          <legend>Signal policy (fixed in v1, not user-configurable)</legend>
          <ul>
            <li>Signals are evaluated at each bar&apos;s close price.</li>
            <li>
              Eligible starting at bar {String(eligibleAfterBarsPreview)} (the warm-up period).
            </li>
            <li>Long-only: no short selling.</li>
            <li>
              Fills happen at the <strong>next bar&apos;s open</strong>, never at the signal
              bar&apos;s close.
            </li>
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
