import {
  ATTRIBUTION_PARAM_KEYS,
  type AttributionParams,
} from "./types";

export const ATTRIBUTION_STORAGE_KEY = "marketchat_attribution";

const MAX_VALUE_LENGTH = 255;

function sanitizeValue(raw: string | null | undefined): string | undefined {
  if (raw == null) return undefined;
  const trimmed = raw.trim().slice(0, MAX_VALUE_LENGTH);
  if (!trimmed) return undefined;
  const cleaned = trimmed.replace(/[<>"'`\\]/g, "");
  return cleaned || undefined;
}

export function parseAttributionFromSearch(search: string): AttributionParams {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const result: AttributionParams = {};

  for (const key of ATTRIBUTION_PARAM_KEYS) {
    const value = sanitizeValue(params.get(key));
    if (value) {
      result[key] = value;
    }
  }

  return result;
}

export function hasAttributionParams(params: AttributionParams): boolean {
  return ATTRIBUTION_PARAM_KEYS.some((key) => Boolean(params[key]));
}

export function saveAttribution(incoming: AttributionParams): AttributionParams {
  const current = loadAttribution();
  const merged: AttributionParams = { ...current };

  for (const key of ATTRIBUTION_PARAM_KEYS) {
    const value = incoming[key];
    if (value && !merged[key]) {
      merged[key] = value;
    }
  }

  try {
    localStorage.setItem(ATTRIBUTION_STORAGE_KEY, JSON.stringify(merged));
  } catch {
    // localStorage indisponível ou quota excedida — ignora silenciosamente
  }

  return merged;
}

export function loadAttribution(): AttributionParams {
  try {
    const raw = localStorage.getItem(ATTRIBUTION_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const result: AttributionParams = {};
    for (const key of ATTRIBUTION_PARAM_KEYS) {
      const value = sanitizeValue(typeof parsed[key] === "string" ? parsed[key] : undefined);
      if (value) {
        result[key] = value;
      }
    }
    return result;
  } catch {
    return {};
  }
}

export function appendAttributionToUrl(baseUrl: string, attribution?: AttributionParams): string {
  const params = attribution ?? loadAttribution();
  if (!hasAttributionParams(params)) {
    return baseUrl;
  }

  const url = new URL(baseUrl);
  for (const key of ATTRIBUTION_PARAM_KEYS) {
    const value = params[key];
    if (value && !url.searchParams.has(key)) {
      url.searchParams.set(key, value);
    }
  }
  return url.toString();
}
