"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { createRun } from "@/lib/api/runs";
import type { ApiError } from "@/lib/api/types";

const POSITIVE_INTEGER = /^[1-9]\d*$/;

interface FormState {
  strategyId: string;
  strategyVersion: string;
  datasetId: string;
  instrumentId: string;
  startDate: string;
  endDate: string;
  capitalAmount: string;
  capitalCurrency: string;
  positionSizingFraction: string;
  quantityIncrement: string;
  moneyScale: string;
  annualizationBasis: string;
  riskFreeRate: string;
}

const INITIAL_FORM: FormState = {
  strategyId: "",
  strategyVersion: "1",
  datasetId: "",
  instrumentId: "",
  startDate: "",
  endDate: "",
  capitalAmount: "1000000.00",
  capitalCurrency: "IDR",
  positionSizingFraction: "0.50",
  quantityIncrement: "1",
  moneyScale: "2",
  annualizationBasis: "252",
  riskFreeRate: "0.00",
};

export default function NewRunPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setSubmitError(null);

    if (!form.strategyId.trim() || !form.datasetId.trim() || !form.instrumentId.trim()) {
      setClientError("Strategy ID, dataset ID, and instrument ID are required.");
      return;
    }
    if (!POSITIVE_INTEGER.test(form.strategyVersion.trim())) {
      setClientError("Strategy version must be a positive whole number.");
      return;
    }
    if (!form.startDate || !form.endDate) {
      setClientError("Start and end dates are required.");
      return;
    }
    if (form.startDate > form.endDate) {
      setClientError("Start date must not be after end date.");
      return;
    }
    if (!POSITIVE_INTEGER.test(form.moneyScale.trim()) && form.moneyScale.trim() !== "0") {
      setClientError("Money scale must be a non-negative whole number.");
      return;
    }
    if (!POSITIVE_INTEGER.test(form.annualizationBasis.trim())) {
      setClientError("Annualization basis must be a positive whole number.");
      return;
    }

    setSubmitting(true);
    const result = await createRun({
      strategy_id: form.strategyId,
      strategy_version: Number(form.strategyVersion),
      dataset_id: form.datasetId,
      instrument_ids: [form.instrumentId],
      start_date: form.startDate,
      end_date: form.endDate,
      capital_amount: form.capitalAmount,
      capital_currency: form.capitalCurrency,
      position_sizing_fraction: form.positionSizingFraction,
      quantity_increment: form.quantityIncrement,
      money_scale: Number(form.moneyScale),
      annualization_basis: Number(form.annualizationBasis),
      risk_free_rate: form.riskFreeRate,
    });
    setSubmitting(false);

    if (!result.ok) {
      setSubmitError(result.error);
      return;
    }
    router.push(`/runs/${result.data.run_id}`);
  }

  return (
    <>
      <h1>Create a run</h1>
      <Disclaimer />
      <p>
        This creates a new, immutable run manifest with status <code>created</code>. It does not
        execute automatically — execute it from the run&apos;s detail page once created. v1 supports
        exactly one instrument per run.
      </p>

      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="strategy_id">Strategy ID</label>
          <input
            id="strategy_id"
            value={form.strategyId}
            onChange={(event) => setForm({ ...form, strategyId: event.target.value })}
            required
            aria-describedby="strategy_id-help"
          />
          <p id="strategy_id-help">
            Copy from the <Link href="/strategies">strategies list</Link>.
          </p>
        </div>

        <div>
          <label htmlFor="strategy_version">Strategy version</label>
          <input
            id="strategy_version"
            inputMode="numeric"
            pattern="[1-9][0-9]*"
            value={form.strategyVersion}
            onChange={(event) => setForm({ ...form, strategyVersion: event.target.value })}
            required
          />
        </div>

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
            Copy from the <Link href="/datasets">datasets list</Link>.
          </p>
        </div>

        <div>
          <label htmlFor="instrument_id">Instrument ID</label>
          <input
            id="instrument_id"
            value={form.instrumentId}
            onChange={(event) => setForm({ ...form, instrumentId: event.target.value })}
            required
            aria-describedby="instrument_id-help"
          />
          <p id="instrument_id-help">Must be mapped to the chosen dataset.</p>
        </div>

        <div>
          <label htmlFor="start_date">Start date</label>
          <input
            id="start_date"
            type="date"
            value={form.startDate}
            onChange={(event) => setForm({ ...form, startDate: event.target.value })}
            required
          />
        </div>

        <div>
          <label htmlFor="end_date">End date</label>
          <input
            id="end_date"
            type="date"
            value={form.endDate}
            onChange={(event) => setForm({ ...form, endDate: event.target.value })}
            required
            aria-describedby="end_date-help"
          />
          <p id="end_date-help">Must be within the dataset&apos;s declared coverage range.</p>
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
          {submitting ? "Creating…" : "Create run"}
        </button>
      </form>

      {submitting && <LoadingState label="Creating run…" />}
      {submitError && <ErrorState error={submitError} />}
    </>
  );
}
