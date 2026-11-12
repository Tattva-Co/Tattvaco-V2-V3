import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectOverviewTool } from "../../../src/components/tools/ProjectOverviewTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: { ...actual.api, projects: { ...actual.api.projects, summary: vi.fn() } },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectOverviewTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

describe("ProjectOverviewTool", () => {
  it("shows the next action, mode distribution and 'none locked' screenplay state honestly", async () => {
    vi.mocked(api.projects.summary).mockResolvedValue({
      project_id: "prj-1",
      project_version: 1,
      canonical_screenplay_version: null,
      screenplay_lock_state: "none_locked",
      scene_count_by_effective_mode: { fully_ai: 2, hybrid_live_action: 1 },
      pending_approvals_count: 3,
      unresolved_high_severity_findings_count: 0,
      running_tasks: [],
      recent_changes: [],
      next_action: { jrn_id: "JRN-01.1", title: "Set the format template", reason: "Required for section 01" },
    });

    renderTool();

    expect(await screen.findByText("Set the format template")).toBeInTheDocument();
    expect(screen.getByText(/No screenplay version is locked yet/)).toBeInTheDocument();
    expect(screen.getByText(/fully ai: 2/)).toBeInTheDocument();
    expect(screen.getByText(/hybrid live action: 1/)).toBeInTheDocument();
    expect(screen.getByText(/3 awaiting a decision/)).toBeInTheDocument();
  });
});
