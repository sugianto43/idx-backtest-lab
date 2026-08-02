import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { WarningsList } from "./WarningsList";

describe("WarningsList", () => {
  it("shows a safe empty message when there are no warnings", () => {
    render(<WarningsList warnings={[]} />);
    expect(screen.getByText("No warnings.")).toBeInTheDocument();
  });

  it("always renders the full warning list alongside the count, not behind a collapsed control", () => {
    render(
      <WarningsList
        warnings={[
          {
            code: "unknown_adjustment_policy",
            message: "Adjustment policy is unknown.",
            sourceRowNumber: null,
          },
          { code: "zero_volume", message: "Row has zero volume.", sourceRowNumber: 42 },
        ]}
      />,
    );

    expect(screen.getByText("2 warnings.")).toBeInTheDocument();
    expect(screen.getByText(/unknown_adjustment_policy/)).toBeInTheDocument();
    expect(screen.getByText(/zero_volume/)).toBeInTheDocument();
    expect(screen.getByText(/row 42/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
