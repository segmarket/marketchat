const STABILITY_CHART_COLORS = [
  "#465FFF",
  "#10B981",
  "#8B5CF6",
  "#F97316",
  "#06B6D4",
  "#EC4899",
  "#EAB308",
  "#6366F1",
] as const;

export function getStabilityColor(index: number): string {
  return STABILITY_CHART_COLORS[index % STABILITY_CHART_COLORS.length];
}
