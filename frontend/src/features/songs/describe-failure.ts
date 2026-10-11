import { ApiError, ConflictError, MissingCsrfTokenError, NetworkError } from "../../lib/api-client";

/** Turns a failed song-library request into a message the administrator can act on. */
export function describeFailure(failure: unknown): string {
  if (failure instanceof ConflictError) {
    const revision = failure.currentRevision;
    return revision === undefined
      ? `${failure.message}. Recarregue a música antes de tentar de novo.`
      : `${failure.message}. Revisão atual: ${revision}. Recarregue a música antes de tentar de novo.`;
  }
  if (failure instanceof ApiError) return failure.message;
  if (failure instanceof MissingCsrfTokenError || failure instanceof NetworkError) return failure.message;
  return "Falha inesperada. Tente novamente.";
}
