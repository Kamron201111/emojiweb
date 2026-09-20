// Central API client. Attaches the session token (or raw initData) to every
// request and normalizes errors into a typed ApiError.

import { getInitData } from "@/lib/telegram";

const BASE = (import.meta.env.VITE_API_BASE as string) || "/api/v1";

let sessionToken: string | null = null;

export function setSessionToken(token: string | null) {
  sessionToken = token;
  if (token) localStorage.setItem("session_token", token);
  else localStorage.removeItem("session_token");
}

export function loadStoredToken(): string | null {
  sessionToken = localStorage.getItem("session_token");
  return sessionToken;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

function authHeader(): Record<string, string> {
  if (sessionToken) return { Authorization: `Bearer ${sessionToken}` };
  const initData = getInitData();
  if (initData) return { Authorization: `tma ${initData}` };
  return {};
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  opts: { auth?: boolean } = { auth: true }
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.auth !== false) Object.assign(headers, authHeader());

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || data.message || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown, opts?: { auth?: boolean }) =>
    request<T>("POST", path, body, opts),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
};
