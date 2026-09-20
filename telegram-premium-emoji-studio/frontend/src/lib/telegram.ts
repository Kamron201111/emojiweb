// Thin wrapper over the Telegram WebApp runtime (window.Telegram.WebApp).
// Provides typed helpers and graceful fallbacks when running outside Telegram
// (e.g. local browser dev), so the UI still works during development.

interface TgWebApp {
  initData: string;
  initDataUnsafe: Record<string, unknown>;
  colorScheme: "light" | "dark";
  themeParams: Record<string, string>;
  version: string;
  platform: string;
  ready: () => void;
  expand: () => void;
  close: () => void;
  openTelegramLink: (url: string) => void;
  openLink: (url: string) => void;
  openInvoice: (url: string, cb?: (status: string) => void) => void;
  HapticFeedback?: {
    impactOccurred: (style: string) => void;
    notificationOccurred: (type: string) => void;
    selectionChanged: () => void;
  };
  MainButton?: {
    setText: (t: string) => void;
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  setHeaderColor?: (c: string) => void;
  setBackgroundColor?: (c: string) => void;
  onEvent?: (event: string, cb: () => void) => void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TgWebApp };
  }
}

export const tg = (): TgWebApp | undefined => window.Telegram?.WebApp;

export function getInitData(): string {
  const w = tg();
  // Fallback: allow ?tgWebAppData= for local testing.
  if (w?.initData) return w.initData;
  const params = new URLSearchParams(window.location.search);
  return params.get("tgWebAppData") || "";
}

export function isInsideTelegram(): boolean {
  return Boolean(tg()?.initData);
}

export function detectColorScheme(): "light" | "dark" {
  const w = tg();
  if (w?.colorScheme) return w.colorScheme;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function haptic(type: "light" | "medium" | "heavy" | "success" | "error" | "warning" | "select" = "light") {
  const h = tg()?.HapticFeedback;
  if (!h) return;
  try {
    if (type === "success" || type === "error" || type === "warning") h.notificationOccurred(type);
    else if (type === "select") h.selectionChanged();
    else h.impactOccurred(type);
  } catch {
    /* no-op */
  }
}

export function openInvoice(url: string): Promise<string> {
  return new Promise((resolve) => {
    const w = tg();
    if (w?.openInvoice) {
      w.openInvoice(url, (status) => resolve(status));
    } else {
      window.open(url, "_blank");
      resolve("unknown");
    }
  });
}

export function openTelegramLink(url: string) {
  const w = tg();
  if (w?.openTelegramLink) w.openTelegramLink(url);
  else window.open(url, "_blank");
}

export function shareLink(url: string, text: string) {
  const share = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
  openTelegramLink(share);
}

export function initTelegram() {
  const w = tg();
  if (!w) return;
  try {
    w.ready();
    w.expand();
  } catch {
    /* no-op */
  }
}
