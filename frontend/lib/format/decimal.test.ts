import { describe, expect, it } from "vitest";
import { formatDecimalString } from "./decimal";

describe("formatDecimalString", () => {
  it("groups large integer parts with thousands separators", () => {
    expect(formatDecimalString("1000000.00")).toBe("1,000,000.00");
  });

  it("preserves full fractional precision, however long", () => {
    expect(formatDecimalString("-0.9999999962730404109454906063")).toBe(
      "-0.9999999962730404109454906063",
    );
  });

  it("leaves small values unchanged", () => {
    expect(formatDecimalString("100")).toBe("100");
  });

  it("handles negative large values", () => {
    expect(formatDecimalString("-1234567.891234")).toBe("-1,234,567.891234");
  });

  it("returns non-decimal-looking strings unchanged rather than throwing", () => {
    expect(formatDecimalString("not_available")).toBe("not_available");
    expect(formatDecimalString("")).toBe("");
  });
});
