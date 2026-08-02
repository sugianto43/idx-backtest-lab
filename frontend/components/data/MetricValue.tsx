import { formatDecimalString } from "@/lib/format/decimal";
import type { MetricValue as MetricValueModel } from "@/lib/api/types";

export function MetricValue({
  label,
  metric,
  currency,
}: {
  label: string;
  metric: MetricValueModel;
  currency?: string;
}) {
  if (metric.status !== "available" || metric.value === null) {
    return (
      <div>
        <dt>{label}</dt>
        <dd>
          Not available
          {metric.reason ? <span> ({metric.reason})</span> : null}
        </dd>
      </div>
    );
  }

  return (
    <div>
      <dt>{label}</dt>
      <dd>
        {formatDecimalString(metric.value)}
        {currency ? ` ${currency}` : ""}
      </dd>
    </div>
  );
}
