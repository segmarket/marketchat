import { useEffect, useMemo } from "react";
import {
  appendAttributionToUrl,
  loadAttribution,
  parseAttributionFromSearch,
  saveAttribution,
} from "../features/attribution/storage";
import type { AttributionParams } from "../features/attribution/types";
import { getAppUrl } from "../utils/host";

export function useUTM() {
  useEffect(() => {
    const fromUrl = parseAttributionFromSearch(window.location.search);
    saveAttribution(fromUrl);
  }, []);

  const attribution = useMemo(() => loadAttribution(), []);

  function buildSignupUrl(path = "/auth/signup"): string {
    return appendAttributionToUrl(getAppUrl(path), loadAttribution());
  }

  return { attribution, buildSignupUrl };
}

export type { AttributionParams };
