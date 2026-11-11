import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * End-to-end parity check for GW3: the full async pipeline through the new React Studio
 * Tools, against a real API, worker and Postgres. This is the one thing no mocked
 * component test can prove -- that an uploaded screenplay really gets parsed by a worker
 * process pulling off the real outbox, and that approving the result really produces a
 * canonical scene the Film Bible tool can read back. It directly exercises the behaviour
 * the old apps/ui (Streamlit) views provided, which this milestone replaces.
 */
test("upload a screenplay, run Script Intelligence, approve it, and see the canonical scene", async ({ page }) => {
  const email = `e2e-pipeline-${Date.now()}@tattva.test`;

  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Your projects" })).toBeVisible();

  await page.getByRole("button", { name: "+ New project" }).click();
  const title = `Pipeline Project ${Date.now()}`;
  await page.getByLabel("Project title").fill(title);
  await page.getByRole("button", { name: "Create project" }).click();
  await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();

  // -- Assets: upload a screenplay -------------------------------------------------
  await page.getByRole("button", { name: "Studio Tools" }).click();
  await page.getByRole("menuitem", { name: /^Assets/ }).click();
  await page
    .getByLabel("Choose a screenplay file")
    .setInputFiles(path.join(__dirname, "fixtures", "sample.fountain"));
  await page.getByRole("button", { name: "Upload & store" }).click();
  await expect(page.getByText("sample.fountain")).toBeVisible();
  await page.getByRole("button", { name: "Close" }).click();

  // -- Script Intelligence: trigger the async graph ---------------------------------
  await page.getByRole("button", { name: "Studio Tools" }).click();
  await page.getByRole("menuitem", { name: "Script Intelligence" }).click();
  await page.getByLabel("Script asset").selectOption({ label: "sample.fountain" });
  await page.getByRole("button", { name: "Run Script Intelligence" }).click();
  await expect(page.getByText(/watch the task tray/)).toBeVisible();
  await page.getByRole("button", { name: "Close" }).click();

  // -- Task tray: wait for the worker to pick the run up and reach the review gate --
  await expect(page.getByRole("button", { name: "Review" })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Review" }).click();

  // -- Review: approve the extracted scene ------------------------------------------
  await expect(page.getByText(/Scene 1/)).toBeVisible();
  await page.getByRole("button", { name: "Approve selected" }).click();
  await expect(page.getByText(/No pending approvals/)).toBeVisible();
  await page.getByRole("button", { name: "Close" }).click();

  // -- Film Bible: the approved scene is now canonical ------------------------------
  await page.getByRole("button", { name: "Studio Tools" }).click();
  await page.getByRole("menuitem", { name: "Film Bible" }).click();
  await page.getByRole("tab", { name: "Scenes" }).click();
  await expect(page.getByText(/Scene 1/)).toBeVisible();
});
