import { api } from "../../services/api";
import type { OnboardingStatus } from "./types";

export async function fetchOnboardingStatus(): Promise<OnboardingStatus> {
  const { data } = await api.get<OnboardingStatus>("/api/onboarding/status/");
  return data;
}

export async function dismissOnboarding(): Promise<OnboardingStatus> {
  const { data } = await api.post<OnboardingStatus>("/api/onboarding/dismiss/");
  return data;
}
