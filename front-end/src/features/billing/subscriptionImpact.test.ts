import { describe, expect, it } from "vitest";
import {
  computeSubscriptionTotals,
  shouldWarnOnMarketCreate,
} from "./subscriptionImpact";

describe("shouldWarnOnMarketCreate", () => {
  it("returns true when adding active market with at least one active market", () => {
    expect(shouldWarnOnMarketCreate(1, "active")).toBe(true);
    expect(shouldWarnOnMarketCreate(2, "active")).toBe(true);
  });

  it("returns false for first active market", () => {
    expect(shouldWarnOnMarketCreate(0, "active")).toBe(false);
  });

  it("returns false when new market is inactive", () => {
    expect(shouldWarnOnMarketCreate(1, "inactive")).toBe(false);
    expect(shouldWarnOnMarketCreate(0, "inactive")).toBe(false);
  });
});

describe("computeSubscriptionTotals", () => {
  it("computes totals from 1 to 2 markets at R$ 59.90", () => {
    const impact = computeSubscriptionTotals(1, 59.9);
    expect(impact.currentTotal).toBe(59.9);
    expect(impact.projectedTotal).toBe(119.8);
    expect(impact.projectedCount).toBe(2);
  });
});
