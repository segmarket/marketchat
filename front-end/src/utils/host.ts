export function isAppHost(hostname = window.location.hostname): boolean {
  return hostname === "app.marketchat.com.br" || hostname.startsWith("app.");
}

export function getAppOrigin(): string {
  const fromEnv = import.meta.env.VITE_APP_ORIGIN?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  return `${window.location.protocol}//app.${window.location.host}`;
}

export function appUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${getAppOrigin()}${normalized}`;
}
