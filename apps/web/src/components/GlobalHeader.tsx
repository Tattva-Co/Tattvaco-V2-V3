import { Link, useNavigate } from "react-router-dom";
import { clearAccessToken } from "../api/auth";

export function GlobalHeader() {
  const navigate = useNavigate();

  function signOut() {
    clearAccessToken();
    navigate("/login", { replace: true });
  }

  return (
    <header className="globalbar">
      <Link to="/" className="brand" aria-label="Tattva Online Workspace">
        <span className="brandmark">T</span>
        <span>
          <span className="brandname">TATTVA</span>
          <span className="brandsub">AI Film Director</span>
        </span>
      </Link>
      <div className="global-actions">
        <button type="button" className="top-link">
          Notifications
        </button>
        <button type="button" className="top-link">
          Help
        </button>
        <button type="button" className="top-link" onClick={signOut}>
          Sign out
        </button>
      </div>
    </header>
  );
}
