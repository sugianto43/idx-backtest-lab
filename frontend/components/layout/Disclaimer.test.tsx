import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Disclaimer } from "./Disclaimer";

describe("Disclaimer", () => {
  it("states backtests are not investment advice", () => {
    render(<Disclaimer />);
    expect(screen.getByText(/not investment advice/)).toBeInTheDocument();
  });
});
