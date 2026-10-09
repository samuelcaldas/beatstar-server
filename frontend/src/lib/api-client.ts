// RED stub: exports the contract names so tests can fail on behaviour, not on import.
export class ApiError extends Error {
  status = 0;
}
export class ConflictError extends ApiError {
  currentRevision = 0;
}
export class UnauthorizedError extends ApiError {}
export class RateLimitedError extends ApiError {
  retryAfterSeconds = 0;
}
export class MissingCsrfTokenError extends Error {}
export class NetworkError extends Error {}

export interface ApiClientOptions {
  baseUrl: string;
  fetch: typeof fetch;
  readCookie: (name: string) => string | undefined;
  onUnauthorized?: () => void;
}

export function createApiClient(_options: ApiClientOptions) {
  return {
    get: async (_path: string, _query?: Record<string, unknown>): Promise<unknown> => {
      throw new Error("not implemented");
    },
    post: async (_path: string, _body: unknown): Promise<unknown> => {
      throw new Error("not implemented");
    },
    patch: async (_path: string, _body: unknown): Promise<unknown> => {
      throw new Error("not implemented");
    },
    delete: async (_path: string, _body: unknown): Promise<unknown> => {
      throw new Error("not implemented");
    },
  };
}
