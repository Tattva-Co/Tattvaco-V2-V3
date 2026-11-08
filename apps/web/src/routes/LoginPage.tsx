import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { setAccessToken } from "../api/auth";

/**
 * The dev-login screen. This talks to POST /auth/dev-login, which only exists when the
 * API runs with environment=development (ADR-003): in staging/production this route
 * 404s, and this screen is where an OIDC redirect flow will go once gate 1 (DEC-002,
 * identity provider vendor) is decided. There is exactly one login screen either way;
 * the backend decides which identity path actually runs.
 */
export function LoginPage() {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await api.auth.devLogin(email.trim(), fullName.trim() || undefined);
      setAccessToken(result.access_token);
      const from = (location.state as { from?: Location })?.from;
      navigate(from ? `${from.pathname}${from.search}` : "/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in. Is the API running?");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={onSubmit}>
        <h1>TATTVA</h1>
        <p>
          Development sign-in. No external identity provider is configured yet (gate 1);
          this issues a short-lived token for the named user in your local Default
          Studio Org.
        </p>
        <input
          id="email"
          type="email"
          aria-label="Email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />
        <input
          id="fullName"
          type="text"
          aria-label="Full name"
          placeholder="Full name (first sign-in only)"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        {error && (
          <p role="alert" style={{ color: "var(--red)" }}>
            {error}
          </p>
        )}
        <button type="submit" className="btn gold" disabled={submitting || !email.trim()}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
