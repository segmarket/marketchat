export type ChatbotAnalyticsCards = {
  total_interactions: number;
  total_interactions_change_pct: number;
  critical_incidents: number;
  critical_incidents_change_pct: number;
};

export type ChatbotAnalyticsRetention = {
  retention_rate: number;
  automated_sessions_count: number;
  support_tickets_count: number;
  cancelled_sessions_count: number;
};

export type HourlyDistributionBucket = {
  label: string;
  count: number;
};

export type StabilitySeriesPoint = {
  date: string;
  line_total_sessions: number;
  line_friction_points: number;
};

export type ChatbotAnalyticsResponse = {
  cards: ChatbotAnalyticsCards;
  retention: ChatbotAnalyticsRetention;
  hourly_distribution: HourlyDistributionBucket[];
  stability_series: StabilitySeriesPoint[];
};
