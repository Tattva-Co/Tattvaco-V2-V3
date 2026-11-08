import { defineConfig, devices } from "@playwright/test";

/**
 * Local-only E2E config (DEC-031, docs/audit/10): it starts a real API process against
 * the same disposable `<db>_test` Postgres database pytest uses (see
 * tests/conftest.py), plus the Vite dev server that proxies /api to it, and runs
 * Playwright against the two together. Not wired into CI yet -- that needs a Postgres
 * service container alongside both processes, tracked as a separate gap.
 *
 * Prerequisites to run `npm run e2e` locally:
 *   - `docker compose up -d` (the Postgres container tests/conftest.py also uses)
 *   - `.venv` created at the repo root with the backend installed (`pip install -e ".[dev]"`)
 */
const API_PORT = 8000;
const WEB_PORT = 5173;
const REPO_ROOT = "../..";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `${REPO_ROOT}/.venv/bin/uvicorn apps.api.main:app --port ${API_PORT}`,
      cwd: REPO_ROOT,
      url: `http://localhost:${API_PORT}/health`,
      reuseExistingServer: true,
      timeout: 30_000,
      env: {
        ENVIRONMENT: "development",
        DATABASE_URL: "postgresql+psycopg://postgres:postgres@localhost:55432/tattva_film_director_test",
        SECRET_KEY: "e2e-local-only-secret-never-used-outside-this-run",
        STORAGE_LOCAL_ROOT: "/tmp/tattva-e2e-storage",
      },
    },
    {
      command: `npm run dev -- --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
