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

  it("guides a first-time visitor to every creation workflow", () => {
    render(<LandingPage />);

    expect(screen.getByRole("link", { name: /import a dataset/i })).toHaveAttribute(
      "href",
      "/datasets/import",
    );
    expect(screen.getByRole("link", { name: /create a strategy/i })).toHaveAttribute(
      "href",
      "/strategies/new",
    );
    expect(screen.getByRole("link", { name: /create a run/i })).toHaveAttribute(
      "href",
      "/runs/new",
    );
    expect(screen.getByRole("link", { name: /create an optimization/i })).toHaveAttribute(
      "href",
      "/optimizations/new",
    );
  });

  it("links to every list page for a returning user", () => {
    render(<LandingPage />);

    for (const href of ["/datasets", "/runs", "/strategies", "/optimizations", "/system"]) {
      expect(
        screen.getByRole("link", { name: new RegExp(`^${href.slice(1)}`, "i") }),
      ).toHaveAttribute("href", href);
    }
  });
});
