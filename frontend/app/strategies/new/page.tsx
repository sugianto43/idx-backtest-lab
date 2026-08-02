"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import {
  createStrategy,
  MAX_COMBO_CONDITIONS,
  MIN_COMBO_CONDITIONS,
  STRATEGY_KINDS,
  strategyKindConfig,
  type BaseStrategyKind,
  type StrategyKind,
} from "@/lib/api/strategies";
import type { ApiError } from "@/lib/api/types";

const POSITIVE_INTEGER = /^[1-9]\d*$/;
const COMBO_KIND_VALUE = "multi_indicator_combo";

function parsePositiveInteger(raw: string): number | null {
  if (!POSITIVE_INTEGER.test(raw.trim())) return null;
  const value = Number(raw.trim());
  return Number.isSafeInteger(value) ? value : null;
}

function defaultFieldValues(kind: BaseStrategyKind): Record<string, string> {
  const config = strategyKindConfig(kind);
  const values: Record<string, string> = {};
  config?.fields.forEach((field) => {
    values[field.key] = String(field.defaultValue);
  });
  return values;
}

function crossFieldError(
  kind: BaseStrategyKind,
  parameters: Record<string, number>,
): string | null {
  if (kind === "sma_crossover" && parameters.fast_window >= parameters.slow_window) {
    return "The fast window must be smaller than the slow window.";
  }
  if (
    kind === "rsi_threshold" &&
    parameters.oversold_threshold >= parameters.overbought_threshold
  ) {
    return "The oversold threshold must be smaller than the overbought threshold.";
  }
  if (kind === "macd_crossover" && parameters.fast_period >= parameters.slow_period) {
    return "The fast period must be smaller than the slow period.";
  }
  return null;
}

interface ComboConditionState {
  kind: BaseStrategyKind;
  fieldValues: Record<string, string>;
}

function defaultComboConditions(): ComboConditionState[] {
  return [
    { kind: "sma_crossover", fieldValues: defaultFieldValues("sma_crossover") },
    { kind: "rsi_threshold", fieldValues: defaultFieldValues("rsi_threshold") },
  ];
}

export default function NewStrategyPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [kind, setKind] = useState<StrategyKind>("sma_crossover");
  const [fieldValues, setFieldValues] = useState<Record<string, string>>(
    defaultFieldValues("sma_crossover"),
  );
  const [comboConditions, setComboConditions] =
    useState<ComboConditionState[]>(defaultComboConditions());
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isCombo = kind === COMBO_KIND_VALUE;
  const config = isCombo ? null : strategyKindConfig(kind)!;

  const parsedPreviewParameters: Record<string, number> = {};
  if (config) {
    for (const field of config.fields) {
      parsedPreviewParameters[field.key] = parsePositiveInteger(fieldValues[field.key] ?? "") ?? 0;
    }
  }
  const singleKindEligiblePreview = config ? config.requiredWarmupBars(parsedPreviewParameters) : 0;
  const comboEligiblePreview = isCombo
    ? Math.max(
        ...comboConditions.map((condition) => {
          const conditionConfig = strategyKindConfig(condition.kind)!;
          const parsed: Record<string, number> = {};
          for (const field of conditionConfig.fields) {
            parsed[field.key] = parsePositiveInteger(condition.fieldValues[field.key] ?? "") ?? 0;
          }
          return conditionConfig.requiredWarmupBars(parsed);
        }),
      )
    : 0;
  const eligibleAfterBarsPreview = isCombo ? comboEligiblePreview : singleKindEligiblePreview;

  function handleKindChange(nextKind: StrategyKind) {
    setKind(nextKind);
    if (nextKind !== COMBO_KIND_VALUE) {
      setFieldValues(defaultFieldValues(nextKind));
    }
    setClientError(null);
  }

  function updateCondition(index: number, updates: Partial<ComboConditionState>) {
    setComboConditions((prev) =>
      prev.map((condition, i) => (i === index ? { ...condition, ...updates } : condition)),
    );
  }

  function addCondition() {
    const usedKinds = new Set(comboConditions.map((c) => c.kind));
    const nextKind = STRATEGY_KINDS.find((k) => !usedKinds.has(k.value))?.value;
    if (!nextKind) return;
    setComboConditions((prev) => [
      ...prev,
      { kind: nextKind, fieldValues: defaultFieldValues(nextKind) },
    ]);
  }

  function removeCondition(index: number) {
    setComboConditions((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setSubmitError(null);

    if (!name.trim()) {
      setClientError("Strategy name is required.");
      return;
    }

    if (isCombo) {
      const kinds = comboConditions.map((c) => c.kind);
      if (new Set(kinds).size !== kinds.length) {
        setClientError("Each condition must use a different indicator.");
        return;
      }
      const conditions: { kind: BaseStrategyKind; parameters: Record<string, number> }[] = [];
      for (const condition of comboConditions) {
        const conditionConfig = strategyKindConfig(condition.kind)!;
        const parameters: Record<string, number> = {};
        for (const field of conditionConfig.fields) {
          const parsed = parsePositiveInteger(condition.fieldValues[field.key] ?? "");
          if (parsed === null) {
            setClientError(`${field.label} must be a positive whole number (no decimals).`);
            return;
          }
          parameters[field.key] = parsed;
        }
        const error = crossFieldError(condition.kind, parameters);
        if (error) {
          setClientError(error);
          return;
        }
        conditions.push({ kind: condition.kind, parameters });
      }

      setSubmitting(true);
      const result = await createStrategy({
        name,
        kind,
        parameters: { conditions },
        eligibleAfterBars: comboEligiblePreview,
      });
      setSubmitting(false);

      if (!result.ok) {
        setSubmitError(result.error);
        return;
      }
      router.push(`/strategies/${result.data.strategy_id}/versions/${result.data.version}`);
      return;
    }

    const parameters: Record<string, number> = {};
    for (const field of config!.fields) {
      const parsed = parsePositiveInteger(fieldValues[field.key] ?? "");
      if (parsed === null) {
        setClientError(`${field.label} must be a positive whole number (no decimals).`);
        return;
      }
      parameters[field.key] = parsed;
    }
    const error = crossFieldError(kind as BaseStrategyKind, parameters);
    if (error) {
      setClientError(error);
      return;
    }

    setSubmitting(true);
    const result = await createStrategy({
      name,
      kind,
      parameters,
      eligibleAfterBars: config!.requiredWarmupBars(parameters),
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
            <option value={COMBO_KIND_VALUE}>Custom (combine indicators)</option>
          </select>
          <p id="kind-help">
            {isCombo
              ? "Combines 2-3 indicator conditions: every condition must signal on the same bar to enter; any one condition signals an exit."
              : config!.description}
          </p>
        </div>

        {!isCombo && (
          <fieldset>
            <legend>{config!.label} parameters</legend>
            {config!.fields.map((field) => (
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
        )}

        {isCombo &&
          comboConditions.map((condition, index) => {
            const conditionConfig = strategyKindConfig(condition.kind)!;
            return (
              <fieldset key={index}>
                <legend>Condition {index + 1}</legend>
                <div>
                  <label htmlFor={`condition-${index}-kind`}>Indicator</label>
                  <select
                    id={`condition-${index}-kind`}
                    value={condition.kind}
                    onChange={(event) =>
                      updateCondition(index, {
                        kind: event.target.value as BaseStrategyKind,
                        fieldValues: defaultFieldValues(event.target.value as BaseStrategyKind),
                      })
                    }
                  >
                    {STRATEGY_KINDS.map((k) => (
                      <option key={k.value} value={k.value}>
                        {k.label}
                      </option>
                    ))}
                  </select>
                </div>
                {conditionConfig.fields.map((field) => (
                  <div key={field.key}>
                    <label htmlFor={`condition-${index}-${field.key}`}>{field.label}</label>
                    <input
                      id={`condition-${index}-${field.key}`}
                      inputMode="numeric"
                      pattern="[1-9][0-9]*"
                      value={condition.fieldValues[field.key] ?? ""}
                      onChange={(event) =>
                        updateCondition(index, {
                          fieldValues: {
                            ...condition.fieldValues,
                            [field.key]: event.target.value,
                          },
                        })
                      }
                      required
                      aria-describedby={`condition-${index}-${field.key}-help`}
                    />
                    <p id={`condition-${index}-${field.key}-help`}>{field.help}</p>
                  </div>
                ))}
                {comboConditions.length > MIN_COMBO_CONDITIONS && (
                  <button type="button" onClick={() => removeCondition(index)}>
                    Remove condition
                  </button>
                )}
              </fieldset>
            );
          })}

        {isCombo && comboConditions.length < MAX_COMBO_CONDITIONS && (
          <button type="button" onClick={addCondition}>
            Add condition
          </button>
        )}

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
