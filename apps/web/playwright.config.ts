import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

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
// Absolute, not a relative string: each webServer entry's `cwd` is resolved independently,
// so a relative "../.." would otherwise need re-deriving per entry instead of reusing one value.
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

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
      command: `.venv/bin/uvicorn apps.api.main:app --port ${API_PORT}`,
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
    {
      // Workflow triggers are async by default (C6): a queued run only progresses once a
      // worker claims it from the outbox. No readiness URL exists for a worker loop, so
      // this entry has neither `url` nor `port` -- Playwright starts it and moves on.
      command: `.venv/bin/python -m apps.worker.worker`,
      cwd: REPO_ROOT,
      reuseExistingServer: true,
      env: {
        ENVIRONMENT: "development",
        DATABASE_URL: "postgresql+psycopg://postgres:postgres@localhost:55432/tattva_film_director_test",
        SECRET_KEY: "e2e-local-only-secret-never-used-outside-this-run",
        STORAGE_LOCAL_ROOT: "/tmp/tattva-e2e-storage",
        WORKER_POLL_INTERVAL_SECONDS: "0.5",
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
