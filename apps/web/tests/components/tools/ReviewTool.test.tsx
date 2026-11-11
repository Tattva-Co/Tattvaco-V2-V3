import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReviewTool } from "../../../src/components/tools/ReviewTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: { ...actual.api, candidates: { get: vi.fn() }, approvals: { decide: vi.fn() } },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReviewTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

const CANDIDATES = {
  scenes: [
    {
      id: "scene-1",
      workflow_run_id: "run-1",
      scene_number: 1,
      heading: "INT. ARCHIVE - NIGHT",
      setting: "interior",
      location_name: "Archive",
      time_of_day: "night",
      summary: "Priya finds the scroll.",
      characters_present: ["Priya"],
      status: "proposed",
    },
  ],
  entities: [
    {
      id: "entity-1",
      workflow_run_id: "run-1",
      name: "Priya",
      category: "character",
      description: null,
      confidence: 0.9,
      status: "proposed",
    },
  ],
  research_claims: [],
  research_questions: [],
  storyboard_panels: [],
  film_bible_rules: [],
  approvals: [
    {
      id: "approval-1",
      workflow_run_id: "run-1",
      scope: "script_intelligence_candidates",
      status: "pending",
      decision: null,
      decided_by: null,
      decided_at: null,
      candidate_summary: {},
    },
  ],
};

describe("ReviewTool", () => {
  beforeEach(() => {
    vi.mocked(api.candidates.get).mockReset();
    vi.mocked(api.approvals.decide).mockReset();
  });

  it("shows a clear empty state when nothing is pending", async () => {
    vi.mocked(api.candidates.get).mockResolvedValue({ scenes: [], entities: [], approvals: [] });
    renderTool();
    expect(await screen.findByText(/No pending approvals/)).toBeInTheDocument();
  });

  it("renders the proposed scene and entity for a pending script-intelligence approval", async () => {
    vi.mocked(api.candidates.get).mockResolvedValue(CANDIDATES as never);
    renderTool();
    expect(await screen.findByText(/Scene 1: INT\. ARCHIVE - NIGHT/)).toBeInTheDocument();
    expect(screen.getByText(/Priya \(90%\)/)).toBeInTheDocument();
  });

  it("approves only the checked candidates, excluding an unchecked one", async () => {
    vi.mocked(api.candidates.get).mockResolvedValue(CANDIDATES as never);
    vi.mocked(api.approvals.decide).mockResolvedValue({
      status: "decision_applied",
      approval_id: "approval-1",
      decision: "approved",
      run_status: "completed",
      new_project_version: 2,
    });
    renderTool();

    const entityCheckbox = await screen.findByLabelText(/Priya \(90%\)/);
    await userEvent.click(entityCheckbox); // uncheck the entity, leave the scene checked

    await userEvent.click(screen.getByRole("button", { name: "Approve selected" }));

    expect(api.approvals.decide).toHaveBeenCalledWith("approval-1", {
      decision: "approved",
      notes: null,
      approved_scene_ids: ["scene-1"],
      approved_entity_ids: [],
      approved_claim_ids: [],
      approved_question_ids: [],
      approved_panel_ids: [],
      approved_rule_ids: [],
    });
  });

  it("rejects without sending any candidate selections", async () => {
    vi.mocked(api.candidates.get).mockResolvedValue(CANDIDATES as never);
    vi.mocked(api.approvals.decide).mockResolvedValue({
      status: "decision_applied",
      approval_id: "approval-1",
      decision: "rejected",
      run_status: "rejected",
      new_project_version: 1,
    });
    renderTool();

    await userEvent.click(await screen.findByRole("button", { name: "Reject all" }));

    expect(api.approvals.decide).toHaveBeenCalledWith("approval-1", { decision: "rejected", notes: null });
  });
});
