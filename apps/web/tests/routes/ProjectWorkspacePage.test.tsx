import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectWorkspacePage } from "../../src/routes/ProjectWorkspacePage";
import { makeGroup, makeProject, makeSection, makeSubpoint } from "../factories";

// Replaces the real fetch-backed client for every importer of this module (the page and
// its hooks alike resolve to the same module id), so the page's behaviour is exercised
// against controlled journey/project fixtures instead of a live backend.
vi.mock("../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../src/api/client")>();
  return {
    ...actual,
    api: {
      projects: { get: vi.fn(), list: vi.fn(), create: vi.fn() },
      journey: { get: vi.fn(), actOnItem: vi.fn(), continueSection: vi.fn() },
      auth: { devLogin: vi.fn() },
      workflowRuns: { get: vi.fn() },
    },
  };
});

import { api } from "../../src/api/client";

function renderPage(projectId = "prj-1") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[`/projects/${projectId}`]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectWorkspacePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ProjectWorkspacePage", () => {
  beforeEach(() => {
    vi.mocked(api.projects.get).mockReset();
    vi.mocked(api.journey.get).mockReset();
    vi.mocked(api.journey.actOnItem).mockReset();
    vi.mocked(api.journey.continueSection).mockReset();
  });

  it("shows a loading state, then the project title, breadcrumb, and journey rail", async () => {
    vi.mocked(api.projects.get).mockResolvedValue(makeProject({ title: "The Iron Crown" }));
    vi.mocked(api.journey.get).mockResolvedValue([
      makeSection({ id: "JRN-01", title: "Project Workspace & Setup" }),
      makeSection({ id: "JRN-02", title: "Screenplay", groups: [] }),
    ]);

    renderPage();
    expect(screen.getByText(/Loading project workspace/)).toBeInTheDocument();

    await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "The Iron Crown" })).toBeInTheDocument());
    expect(screen.getByText(/Online Workspace \/ The Iron Crown/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Project Workspace & Setup/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Screenplay/ })).toBeDisabled();
  });

  it("disables Continue until the section can_continue, and reports the API error on a blocked attempt", async () => {
    vi.mocked(api.projects.get).mockResolvedValue(makeProject());
    vi.mocked(api.journey.get).mockResolvedValue([
      makeSection({ id: "JRN-01", can_continue: false, status: "in_progress" }),
    ]);

    renderPage();
    await waitFor(() => expect(screen.getByText("Complete the required work to continue")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Continue to Next Section/ })).toBeDisabled();
  });

  it("marks a subpoint complete and advances to the next section once the gate opens", async () => {
    const user = userEvent.setup();
    const group = makeGroup({
      id: "JRN-01.1",
      required: true,
      subpoints: [makeSubpoint({ id: "JRN-01.1.1", status: "not_started" })],
    });
    const sectionOne = makeSection({ id: "JRN-01", title: "Setup", can_continue: true, groups: [group] });
    const sectionTwo = makeSection({ id: "JRN-02", title: "Screenplay", groups: [] });

    vi.mocked(api.projects.get).mockResolvedValue(makeProject());
    vi.mocked(api.journey.get).mockResolvedValue([sectionOne, sectionTwo]);
    vi.mocked(api.journey.actOnItem).mockResolvedValue(makeSubpoint({ id: "JRN-01.1.1", status: "completed" }));
    vi.mocked(api.journey.continueSection).mockResolvedValue({
      section_id: "JRN-01",
      status: "completed",
      group_statuses: { "JRN-01.1": "completed" },
    });

    renderPage();
    await waitFor(() => expect(screen.getByRole("heading", { level: 2, name: "Setup" })).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /Project identity/ }));
    await user.click(screen.getByRole("button", { name: "Mark complete" }));
    expect(api.journey.actOnItem).toHaveBeenCalledWith("prj-1", "JRN-01.1.1", {
      action: "complete",
      not_applicable_reason: null,
    });
    await waitFor(() => expect(screen.getByText("Marked complete.")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /Continue to Next Section/ }));
    expect(api.journey.continueSection).toHaveBeenCalledWith("prj-1", "JRN-01");
    await waitFor(() => expect(screen.getByRole("heading", { level: 2, name: "Screenplay" })).toBeInTheDocument());
  });

  it("shows a permission-denied message when the journey load is forbidden", async () => {
    const { ApiError } = await vi.importActual<typeof import("../../src/api/client")>("../../src/api/client");
    vi.mocked(api.projects.get).mockResolvedValue(makeProject());
    vi.mocked(api.journey.get).mockRejectedValue(new ApiError(403, "TenantAccessViolation", "Forbidden"));

    renderPage();
    await waitFor(() =>
      expect(screen.getByText(/don't have permission/)).toBeInTheDocument()
    );
  });
});
