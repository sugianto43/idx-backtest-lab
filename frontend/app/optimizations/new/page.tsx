"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useMemo, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import {
  createOptimization,
  OBJECTIVE_METRIC_KEYS,
  type ObjectiveMetricKey,
} from "@/lib/api/optimizations";
import type { ApiError } from "@/lib/api/types";

const POSITIVE_INTEGER_LIST = /^\s*[1-9]\d*\s*(,\s*[1-9]\d*\s*)*$/;

function parseIntegerList(raw: string): number[] | null {
  if (!POSITIVE_INTEGER_LIST.test(raw)) return null;
  const values = raw.split(",").map((part) => Number(part.trim()));
  return values.every((value) => Number.isSafeInteger(value)) ? values : null;
}

function countValidPairs(fastWindows: number[], slowWindows: number[]): number {
  const fastSet = [...new Set(fastWindows)];
  const slowSet = [...new Set(slowWindows)];
  let count = 0;
  for (const fast of fastSet) {
    for (const slow of slowSet) {
      if (fast < slow) count += 1;
    }
  }
  return count;
}

interface FormState {
  datasetId: string;
  instrumentId: string;
  baseStrategyName: string;
  fastWindows: string;
  slowWindows: string;
  trainStart: string;
  trainEnd: string;
  validationStart: string;
  validationEnd: string;
  holdoutStart: string;
  holdoutEnd: string;
  capitalAmount: string;
  capitalCurrency: string;
  positionSizingFraction: string;
  quantityIncrement: string;
  moneyScale: string;
  annualizationBasis: string;
  riskFreeRate: string;
  objectiveMetricKey: ObjectiveMetricKey;
}

const INITIAL_FORM: FormState = {
  datasetId: "",
  instrumentId: "",
  baseStrategyName: "",
  fastWindows: "",
  slowWindows: "",
  trainStart: "",
  trainEnd: "",
  validationStart: "",
  validationEnd: "",
  holdoutStart: "",
  holdoutEnd: "",
  capitalAmount: "1000000.00",
  capitalCurrency: "IDR",
  positionSizingFraction: "0.50",
  quantityIncrement: "1",
  moneyScale: "2",
  annualizationBasis: "252",
  riskFreeRate: "0.00",
  objectiveMetricKey: "total_return",
};

export default function NewOptimizationPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const previewCandidateCount = useMemo(() => {
    const fastWindows = parseIntegerList(form.fastWindows);
    const slowWindows = parseIntegerList(form.slowWindows);
    if (fastWindows === null || slowWindows === null) return null;
    return countValidPairs(fastWindows, slowWindows);
  }, [form.fastWindows, form.slowWindows]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setSubmitError(null);

    const fastWindows = parseIntegerList(form.fastWindows);
    const slowWindows = parseIntegerList(form.slowWindows);
    if (fastWindows === null || slowWindows === null) {
      setClientError(
        "Fast/slow windows must be comma-separated positive whole numbers (e.g. 2, 3, 5).",
      );
      return;
    }
    if (!form.datasetId.trim() || !form.instrumentId.trim() || !form.baseStrategyName.trim()) {
      setClientError("Dataset ID, instrument ID, and a base strategy name are required.");
      return;
    }
    if (
      !form.trainStart ||
      !form.trainEnd ||
      !form.validationStart ||
      !form.validationEnd ||
      !form.holdoutStart ||
      !form.holdoutEnd
    ) {
      setClientError("All six train/validation/holdout partition dates are required.");
      return;
    }
    if (!(
      form.trainStart <= form.trainEnd &&
      form.trainEnd < form.validationStart &&
      form.validationStart <= form.validationEnd &&
      form.validationEnd < form.holdoutStart &&
      form.holdoutStart <= form.holdoutEnd
    )) {
      setClientError(
        "Partitions must be chronological and non-overlapping: train ends before validation " +
          "starts, and validation ends before holdout starts.",
      );
      return;
    }

    setSubmitting(true);
    const result = await createOptimization({
      dataset_id: form.datasetId,
      instrument_id: form.instrumentId,
      base_strategy_name: form.baseStrategyName,
      fast_windows: fastWindows,
      slow_windows: slowWindows,
      train_start: form.trainStart,
      train_end: form.trainEnd,
      validation_start: form.validationStart,
      validation_end: form.validationEnd,
      holdout_start: form.holdoutStart,
      holdout_end: form.holdoutEnd,
      capital_amount: form.capitalAmount,
      capital_currency: form.capitalCurrency,
      position_sizing_fraction: form.positionSizingFraction,
      quantity_increment: form.quantityIncrement,
      money_scale: Number(form.moneyScale),
      annualization_basis: Number(form.annualizationBasis),
      risk_free_rate: form.riskFreeRate,
      objective_metric_key: form.objectiveMetricKey,
    });
    setSubmitting(false);

    if (!result.ok) {
      setSubmitError(result.error);
      return;
    }
    router.push(`/optimizations/${result.data.optimization_id}`);
  }

  return (
    <>
      <h1>Create an optimization</h1>
      <Disclaimer />
      <p>
        This creates a new, immutable optimization manifest. Every candidate, rejection, and failure
        is recorded and visible — nothing is silently dropped or retried. Selection on historical
        validation data may be overfit and does not predict future performance; the holdout
        evaluation is sealed until the optimization completes.
      </p>

      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="dataset_id">Dataset ID</label>
          <input
            id="dataset_id"
            value={form.datasetId}
            onChange={(event) => setForm({ ...form, datasetId: event.target.value })}
            required
            aria-describedby="dataset_id-help"
          />
          <p id="dataset_id-help">
            Copy the dataset ID from the <Link href="/datasets">datasets list</Link>.
          </p>
        </div>

        <div>
          <label htmlFor="instrument_id">Instrument ID</label>
          <input
            id="instrument_id"
            value={form.instrumentId}
            onChange={(event) => setForm({ ...form, instrumentId: event.target.value })}
            required
          />
        </div>

        <div>
          <label htmlFor="base_strategy_name">Base strategy name</label>
          <input
            id="base_strategy_name"
            value={form.baseStrategyName}
            onChange={(event) => setForm({ ...form, baseStrategyName: event.target.value })}
            required
            aria-describedby="base_strategy_name-help"
          />
          <p id="base_strategy_name-help">
            Each candidate creates its own immutable strategy version labeled with this name plus
            its fast/slow windows.
          </p>
        </div>

        <div>
          <label htmlFor="fast_windows">Fast SMA windows</label>
          <input
            id="fast_windows"
            value={form.fastWindows}
            onChange={(event) => setForm({ ...form, fastWindows: event.target.value })}
            required
            aria-describedby="fast_windows-help"
            placeholder="2, 3"
          />
          <p id="fast_windows-help">Comma-separated positive whole numbers.</p>
        </div>

        <div>
          <label htmlFor="slow_windows">Slow SMA windows</label>
          <input
            id="slow_windows"
            value={form.slowWindows}
            onChange={(event) => setForm({ ...form, slowWindows: event.target.value })}
            required
            aria-describedby="slow_windows-help"
            placeholder="4, 5"
          />
          <p id="slow_windows-help">Comma-separated positive whole numbers.</p>
        </div>

        <p role="status">
          Candidate count: {previewCandidateCount === null ? "—" : previewCandidateCount} valid pair
          {previewCandidateCount === 1 ? "" : "s"} (fast_window &lt; slow_window). Invalid pairs are
          still recorded as rejected, not silently dropped.
        </p>

        <fieldset>
          <legend>Chronological partitions</legend>
          <div>
            <label htmlFor="train_start">Train start</label>
            <input
              id="train_start"
              type="date"
              value={form.trainStart}
              onChange={(event) => setForm({ ...form, trainStart: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="train_end">Train end</label>
            <input
              id="train_end"
              type="date"
              value={form.trainEnd}
              onChange={(event) => setForm({ ...form, trainEnd: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="validation_start">Validation start</label>
            <input
              id="validation_start"
              type="date"
              value={form.validationStart}
              onChange={(event) => setForm({ ...form, validationStart: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="validation_end">Validation end</label>
            <input
              id="validation_end"
              type="date"
              value={form.validationEnd}
              onChange={(event) => setForm({ ...form, validationEnd: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="holdout_start">Holdout start</label>
            <input
              id="holdout_start"
              type="date"
              value={form.holdoutStart}
              onChange={(event) => setForm({ ...form, holdoutStart: event.target.value })}
              required
              aria-describedby="holdout_start-help"
            />
            <p id="holdout_start-help">
              Sealed until the optimization completes — it cannot influence which candidate is
              selected.
            </p>
          </div>
          <div>
            <label htmlFor="holdout_end">Holdout end</label>
            <input
              id="holdout_end"
              type="date"
              value={form.holdoutEnd}
              onChange={(event) => setForm({ ...form, holdoutEnd: event.target.value })}
              required
            />
          </div>
        </fieldset>

        <div>
          <label htmlFor="objective_metric_key">Objective metric</label>
          <select
            id="objective_metric_key"
            value={form.objectiveMetricKey}
            onChange={(event) =>
              setForm({ ...form, objectiveMetricKey: event.target.value as ObjectiveMetricKey })
            }
          >
            {OBJECTIVE_METRIC_KEYS.map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
          </select>
          <p>
            Candidates are ranked only by this validation-period metric. An unavailable objective
            can never win. Tie-break: highest value, then lower slow window, then lower fast window,
            then candidate ID.
          </p>
        </div>

        <fieldset>
          <legend>Capital and execution assumptions</legend>
          <div>
            <label htmlFor="capital_amount">Capital amount</label>
            <input
              id="capital_amount"
              value={form.capitalAmount}
              onChange={(event) => setForm({ ...form, capitalAmount: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="capital_currency">Capital currency</label>
            <input
              id="capital_currency"
              value={form.capitalCurrency}
              onChange={(event) => setForm({ ...form, capitalCurrency: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="position_sizing_fraction">Position sizing fraction</label>
            <input
              id="position_sizing_fraction"
              value={form.positionSizingFraction}
              onChange={(event) => setForm({ ...form, positionSizingFraction: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="quantity_increment">Quantity increment</label>
            <input
              id="quantity_increment"
              value={form.quantityIncrement}
              onChange={(event) => setForm({ ...form, quantityIncrement: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="money_scale">Money scale (decimal places)</label>
            <input
              id="money_scale"
              inputMode="numeric"
              pattern="[0-9]*"
              value={form.moneyScale}
              onChange={(event) => setForm({ ...form, moneyScale: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="annualization_basis">Annualization basis (sessions/year)</label>
            <input
              id="annualization_basis"
              inputMode="numeric"
              pattern="[1-9][0-9]*"
              value={form.annualizationBasis}
              onChange={(event) => setForm({ ...form, annualizationBasis: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="risk_free_rate">Risk-free rate</label>
            <input
              id="risk_free_rate"
              value={form.riskFreeRate}
              onChange={(event) => setForm({ ...form, riskFreeRate: event.target.value })}
              required
            />
          </div>
        </fieldset>

        {clientError ? <p role="alert">{clientError}</p> : null}

        <button type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create optimization"}
        </button>
      </form>

      {submitting && <LoadingState label="Creating optimization…" />}
      {submitError && <ErrorState error={submitError} />}
    </>
  );
}
