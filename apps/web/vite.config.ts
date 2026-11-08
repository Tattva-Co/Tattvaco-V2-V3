/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": "/src" },
  },
  server: {
    port: 5173,
    proxy: {
      // The dev API runs on :8000 (uvicorn apps.api.main:app --reload); the web app
      // never hardcodes the API origin so the same build works behind any reverse
      // proxy in staging/production (ADR-002).
      "/api": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    // e2e/ holds Playwright specs (run by `npx playwright test`, DEC-031). Vitest must not
    // collect them, or `npm test` (the CI unit-test step) fails on Playwright's test().
    exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"],
  },
});
