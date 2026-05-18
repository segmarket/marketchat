export type OnboardingStatus = {
  step_market_created: boolean;
  step_product_created: boolean;
  step_whatsapp_connected: boolean;
  step_test_order_completed: boolean;
  onboarding_finished: boolean;
  completed_count: number;
  completion_percent: number;
  show_mission_panel: boolean;
};
