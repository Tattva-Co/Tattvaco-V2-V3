import { ApiError, UnauthenticatedError } from "../api/client";

/** One error-to-copy mapping shared by every page and Studio Tool, so "you're signed out"
 * and "you don't have permission" always read the same way no matter where they happen
 * to surface. Permission checks for Studio Tools are enforced server-side (AuthzService);
 * this is how a 403 from that enforcement becomes visible rather than a generic failure. */
export function describeError(err: unknown): string {
  if (err instanceof UnauthenticatedError) return "Your session has expired. Please sign in again.";
  if (err instanceof ApiError) {
    if (err.status === 403) return "You don't have permission to do that on this project.";
    return err.message || "Something went wrong.";
  }
  return "Something went wrong.";
}
