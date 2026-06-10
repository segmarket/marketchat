export type SubscriptionImpact = {
  activeCount: number;
  projectedCount: number;
  unitPrice: number;
  currentTotal: number;
  projectedTotal: number;
};

const DEFAULT_UNIT_PRICE = 59.9;

export function getUnitPrice(): number {
  const raw = import.meta.env.VITE_PLAN_PRICE?.trim();
  if (!raw) return DEFAULT_UNIT_PRICE;
  const normalized = raw.replace(",", ".");
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : DEFAULT_UNIT_PRICE;
}

export function computeSubscriptionTotals(
  activeCount: number,
  unitPrice: number = getUnitPrice(),
): SubscriptionImpact {
  const projectedCount = activeCount + 1;
  return {
    activeCount,
    projectedCount,
    unitPrice,
    currentTotal: roundMoney(activeCount * unitPrice),
    projectedTotal: roundMoney(projectedCount * unitPrice),
  };
}

export function shouldWarnOnMarketCreate(
  activeMarketsCount: number,
  newStatus: "active" | "inactive",
): boolean {
  return newStatus === "active" && activeMarketsCount >= 1;
}

function roundMoney(value: number): number {
  return Math.round(value * 100) / 100;
}
