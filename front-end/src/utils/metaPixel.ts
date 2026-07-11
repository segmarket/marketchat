import { isAppHost } from "./host";

const META_PIXEL_SCRIPT_ID = "marketchat-meta-pixel-script";

const MARKETING_PUBLIC_PATHS = new Set(["/", "/consultoria", "/privacidade", "/termos", "/links"]);

const APP_PUBLIC_PATHS = new Set([
  "/signin",
  "/login",
  "/auth/signup",
  "/signup",
  "/register",
  "/reset-password",
  "/privacidade",
  "/termos",
]);

type FbqCommand = "init" | "track";
type FbqFunction = {
  (...args: unknown[]): void;
  callMethod?: (...args: unknown[]) => void;
  queue: unknown[][];
  loaded?: boolean;
  version?: string;
  push: FbqFunction;
};

declare global {
  interface Window {
    fbq?: FbqFunction;
    _fbq?: FbqFunction;
  }
}

export function getMetaPixelId(): string | undefined {
  const id = import.meta.env.VITE_META_PIXEL_ID?.trim();
  return id || undefined;
}

export function isPublicPagePath(pathname: string, onAppHost = isAppHost()): boolean {
  const path = pathname || "/";
  if (onAppHost) {
    return APP_PUBLIC_PATHS.has(path);
  }
  return MARKETING_PUBLIC_PATHS.has(path);
}

function callFbq(command: FbqCommand, ...args: unknown[]): void {
  if (typeof window.fbq !== "function") return;
  window.fbq(command, ...args);
}

function injectMetaPixelScript(): void {
  if (typeof document === "undefined") return;
  if (document.getElementById(META_PIXEL_SCRIPT_ID)) return;

  const fbq: FbqFunction = function (...args: unknown[]) {
    if (fbq.callMethod) {
      fbq.callMethod(...args);
      return;
    }
    fbq.queue.push(args);
  } as FbqFunction;
  fbq.push = fbq;
  fbq.loaded = true;
  fbq.version = "2.0";
  fbq.queue = [];

  if (!window.fbq) {
    window.fbq = fbq;
  }
  if (!window._fbq) {
    window._fbq = window.fbq;
  }

  const script = document.createElement("script");
  script.id = META_PIXEL_SCRIPT_ID;
  script.async = true;
  script.src = "https://connect.facebook.net/en_US/fbevents.js";
  const firstScript = document.getElementsByTagName("script")[0];
  firstScript?.parentNode?.insertBefore(script, firstScript);
}

let pixelInitialized = false;

/** Carrega fbq, init e primeiro PageView — uma vez por sessão após consentimento. */
export function initMetaPixel(): void {
  const pixelId = getMetaPixelId();
  if (!pixelId || pixelInitialized) return;

  try {
    injectMetaPixelScript();
    callFbq("init", pixelId);
    callFbq("track", "PageView");
    pixelInitialized = true;
  } catch {
    // fail-safe: adblockers não devem quebrar a UI
  }
}

/** PageView em navegação SPA (sem re-init). */
export function trackMetaPageView(): void {
  if (!pixelInitialized || !getMetaPixelId()) return;

  try {
    callFbq("track", "PageView");
  } catch {
    // ignore
  }
}

export function isMetaPixelInitialized(): boolean {
  return pixelInitialized;
}
