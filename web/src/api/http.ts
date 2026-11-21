import type { components } from "./schema";

type ErrorEnvelope = components["schemas"]["ErrorResponse"];

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>[] | null;
  readonly retryAfter: number | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown>[] | null = null,
    retryAfter: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.retryAfter = retryAfter;
  }
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

let csrfToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

/** The CSRF token of the current cookie session, as reported by `auth/me`. */
export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

/** Called when a request that needed a session comes back 401. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

async function toApiError(resp: Response): Promise<ApiError> {
  const header = resp.headers.get("Retry-After");
  const retryAfter = header !== null && /^\d+$/.test(header) ? Number(header) : null;
  try {
    const body = (await resp.json()) as Partial<ErrorEnvelope>;
    if (body.error) {
      return new ApiError(
        resp.status,
        body.error.code,
        body.error.message,
        body.error.details ?? null,
        retryAfter,
      );
    }
  } catch {
    // Not JSON (a proxy error page, say): fall through to the generic error.
  }
  return new ApiError(resp.status, "http_error", `HTTP ${resp.status}`, null, retryAfter);
}

/**
 * Calls the Engine API. `path` is relative to `api/v1/` and the URL has no leading slash
 * on purpose: under Home Assistant Ingress the page lives at
 * /api/hassio_ingress/<token>/, and absolute paths would escape it.
 */
export async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; signal?: AbortSignal; session?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (UNSAFE.has(method) && csrfToken) {
    headers["X-TVBalance-CSRF"] = csrfToken;
  }
  const resp = await fetch(`api/v1/${path}`, {
    method,
    headers,
    credentials: "same-origin",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
  if (!resp.ok) {
    if (resp.status === 401 && options.session !== false) {
      onUnauthorized?.();
    }
    throw await toApiError(resp);
  }
  if (resp.status === 204) {
    return undefined as T;
  }
  return (await resp.json()) as T;
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>("GET", path, { signal }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  delete: <T>(path: string) => request<T>("DELETE", path),
};
