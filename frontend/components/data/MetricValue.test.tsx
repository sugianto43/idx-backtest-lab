import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MetricValue } from "./MetricValue";

describe("MetricValue", () => {
  it("renders an available value formatted for display, never recomputed", () => {
    render(
      <dl>
        <MetricValue
          label="Final equity"
          metric={{ status: "available", value: "1000000.00", reason: null }}
        />
      </dl>,
    );

    expect(screen.getByText("Final equity")).toBeInTheDocument();
    expect(screen.getByText("1,000,000.00")).toBeInTheDocument();
  });

  it("never renders a not_available metric as zero or blank", () => {
    render(
      <dl>
        <MetricValue
          label="Win rate"
          metric={{ status: "not_available", value: null, reason: "zero_trades" }}
        />
      </dl>,
    );

    expect(screen.queryByText("0")).not.toBeInTheDocument();
    expect(screen.getByText(/Not available/)).toBeInTheDocument();
    expect(screen.getByText(/zero_trades/)).toBeInTheDocument();
  });

  it("appends a currency label when provided", () => {
    render(
      <dl>
        <MetricValue
          label="Final equity"
          metric={{ status: "available", value: "500.00", reason: null }}
          currency="IDR"
        />
      </dl>,
    );

    expect(screen.getByText("500.00 IDR")).toBeInTheDocument();
  });
});
