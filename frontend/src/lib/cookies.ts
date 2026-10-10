/**
 * Reads one cookie from a document.cookie string.
 *
 * Returns undefined for a missing or empty value, so callers that require a token
 * (for example the CSRF header) fail before sending a request the server would reject.
 */
export function readCookie(cookieHeader: string, name: string): string | undefined {
  for (const pair of cookieHeader.split(";")) {
    const separator = pair.indexOf("=");
    if (separator === -1) continue;
    if (pair.slice(0, separator).trim() !== name) continue;
    const value = pair.slice(separator + 1).trim();
    return value === "" ? undefined : value;
  }
  return undefined;
}
