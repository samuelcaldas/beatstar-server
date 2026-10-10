/**
 * Typed HTTP client for the administration API.
 *
 * Every request is same-origin with credentials, so the HttpOnly session cookie travels
 * automatically. Writes additionally echo the CSRF cookie in the X-CSRF-Token header; the
 * client refuses to send a write it cannot protect instead of letting the server reject it.
 */

export const CSRF_COOKIE = "beatstar_admin_csrf";
export const CSRF_HEADER = "X-CSRF-Token";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = new.target.name;
    this.status = status;
  }
}

export class UnauthorizedError extends ApiError {}

export class ConflictError extends ApiError {
  readonly currentRevision: number | undefined;

  constructor(message: string, currentRevision: number | undefined) {
    super(409, message);
    this.currentRevision = currentRevision;
  }
}

export class RateLimitedError extends ApiError {
  readonly retryAfterSeconds: number | undefined;

  constructor(message: string, retryAfterSeconds: number | undefined) {
    super(429, message);
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export class MissingCsrfTokenError extends Error {}

export class NetworkError extends Error {
  constructor(cause: unknown) {
    super("Não foi possível conectar ao servidor");
    this.cause = cause;
  }
}

export interface ApiClientOptions {
  baseUrl: string;
  fetch: typeof fetch;
  readCookie: (name: string) => string | undefined;
  onUnauthorized?: () => void;
}

type QueryValue = string | number | boolean | null | undefined;
type Method = "GET" | "POST" | "PATCH" | "DELETE";

export interface ApiClient {
  get<T = unknown>(path: string, query?: Record<string, QueryValue>): Promise<T>;
  post<T = unknown>(path: string, body?: unknown): Promise<T>;
  patch<T = unknown>(path: string, body?: unknown): Promise<T>;
  delete<T = unknown>(path: string, body?: unknown): Promise<T>;
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const request = <T>(method: Method, path: string, payload?: { query?: Record<string, QueryValue>; body?: unknown }) =>
    send<T>(options, method, path, payload);

  return {
    get: (path, query) => request("GET", path, { query }),
    post: (path, body) => request("POST", path, { body }),
    patch: (path, body) => request("PATCH", path, { body }),
    delete: (path, body) => request("DELETE", path, { body }),
  };
}

async function send<T>(
  options: ApiClientOptions,
  method: Method,
  path: string,
  payload: { query?: Record<string, QueryValue>; body?: unknown } = {},
): Promise<T> {
  const headers = new Headers();
  if (method !== "GET") {
    const token = options.readCookie(CSRF_COOKIE);
    if (!token) {
      throw new MissingCsrfTokenError("Token CSRF ausente; recarregue a página e entre novamente");
    }
    headers.set(CSRF_HEADER, token);
  }
  let body: string | undefined;
  if (payload.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(payload.body);
  }

  const url = buildUrl(options.baseUrl, path, payload.query);
  let response: Response;
  try {
    response = await options.fetch(url, { method, headers, body, credentials: "same-origin" });
  } catch (cause) {
    throw new NetworkError(cause);
  }

  if (response.ok) {
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  }
  throw await toError(response, options);
}

function buildUrl(baseUrl: string, path: string, query?: Record<string, QueryValue>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const suffix = params.toString();
  return `${baseUrl}${path}${suffix ? `?${suffix}` : ""}`;
}

async function toError(response: Response, options: ApiClientOptions): Promise<ApiError> {
  const document = await readJson(response);
  const detail = typeof document?.detail === "string" ? document.detail : `Erro HTTP ${response.status}`;

  if (response.status === 401) {
    options.onUnauthorized?.();
    return new UnauthorizedError(response.status, detail);
  }
  if (response.status === 409) {
    const current = typeof document?.current_revision === "number" ? document.current_revision : undefined;
    return new ConflictError(detail, current);
  }
  if (response.status === 429) {
    const header = Number(response.headers.get("retry-after"));
    return new RateLimitedError(detail, Number.isFinite(header) && header > 0 ? header : undefined);
  }
  return new ApiError(response.status, detail);
}

async function readJson(response: Response): Promise<Record<string, unknown> | undefined> {
  try {
    const parsed: unknown = JSON.parse(await response.text());
    return typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : undefined;
  } catch {
    return undefined;
  }
}
