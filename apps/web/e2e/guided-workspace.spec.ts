import { test, expect } from "@playwright/test";

/**
 * End-to-end smoke test for the GW2 production workspace shell, against a real API and
 * Postgres (see playwright.config.ts). It exercises the one path that matters most: sign
 * in, create a project, and make real progress through the guided journey -- the thing
 * no component test can verify, because it depends on the actual journey engine
 * (packages/services/journey.py) deriving real statuses from real persisted state.
 */
test("sign in, create a project, and complete a journey subpoint", async ({ page }) => {
  const email = `e2e-${Date.now()}@tattva.test`;

  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Full name").fill("E2E Test User");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Your projects" })).toBeVisible();

  await page.getByRole("button", { name: "+ New project" }).click();
  const title = `E2E Project ${Date.now()}`;
  await page.getByLabel("Project title").fill(title);
  await page.getByRole("button", { name: "Create project" }).click();

  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
  await expect(page.getByRole("button", { name: /Project Workspace & Setup/ })).toHaveAttribute(
    "aria-current",
    "step"
  );

  // Every other section must still be locked on a brand-new project.
  await expect(page.getByRole("button", { name: /Screenplay/ })).toBeDisabled();

  await page.getByRole("button", { name: /Project identity/ }).click();
  const subpointRow = page.locator(".subpoint").first();
  await expect(subpointRow.getByText("Not started")).toBeVisible();

  await subpointRow.getByRole("button", { name: "Mark complete" }).click();
  await expect(subpointRow.getByText("Completed")).toBeVisible();
  await expect(page.getByText("Marked complete.")).toBeVisible();
});
