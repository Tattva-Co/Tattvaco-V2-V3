import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated } from "../api/auth";

/**
 * Redirects to /login when there is no access token. Reads sessionStorage directly on
 * every render rather than through a subscription: the token only ever changes via our
 * own setAccessToken/clearAccessToken calls, and both of those are always immediately
 * followed by a navigation (LoginPage on success, ApiError handling on a 401), which
 * already forces this component to re-render and re-check.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}
