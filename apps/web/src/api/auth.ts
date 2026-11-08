/**
 * Access-token storage for the browser session (ADR-003). There is no refresh-token
 * flow yet: a dev token's lifetime matches ACCESS_TOKEN_TTL_SECONDS (1h default), and
 * when it expires the next API call 401s, UnauthenticatedError is thrown, and the app
 * returns to the login screen. That is an acceptable gap for the dev-token path; an
 * OIDC vendor (gate 1, still open) will bring its own refresh handling.
 *
 * sessionStorage, not localStorage: a token should not outlive the browser tab by
 * default, and every environment this talks to (dev, and later staging/prod once an
 * OIDC provider exists) treats a fresh login as the normal flow, not a liability to
 * avoid.
 */
const STORAGE_KEY = "tattva.access_token";

export function getAccessToken(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, token);
  } catch {
    // Storage can throw in a private-browsing context with blocked storage; the app
    // still works for the current render, it just won't survive a reload.
  }
}

export function clearAccessToken(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // see setAccessToken
  }
}

export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}
