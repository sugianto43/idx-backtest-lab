import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LandingPage from "./page";

describe("LandingPage", () => {
  it("renders exactly one accessible page heading", () => {
    render(<LandingPage />);

    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent("IDX Backtesting Lab");
  });

  it("does not render its own main landmark (the root layout owns it)", () => {
    render(<LandingPage />);

    expect(screen.queryByRole("main")).not.toBeInTheDocument();
  });
});
