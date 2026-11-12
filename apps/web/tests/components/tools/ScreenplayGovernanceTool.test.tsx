import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScreenplayGovernanceTool } from "../../../src/components/tools/ScreenplayGovernanceTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      screenplay: {
        listVersions: vi.fn(),
        getVersion: vi.fn(),
        importVersion: vi.fn(),
        updateVersion: vi.fn(),
        diff: vi.fn(),
        revise: vi.fn(),
        submit: vi.fn(),
        decide: vi.fn(),
        confirmLegacyLock: vi.fn(),
        previewImpact: vi.fn(),
        generateSuggestions: vi.fn(),
        listSuggestions: vi.fn(),
        decideSuggestion: vi.fn(),
        listImpactAnalyses: vi.fn(),
      },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ScreenplayGovernanceTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

function makeVersion(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "version-1",
    project_id: "prj-1",
    episode_id: null,
    version_number: 1,
    status: "draft",
    is_production_canonical: false,
    source_asset_id: "asset-1",
    derived_from_version_id: null,
    content_text: "EXT. SCENE - DAY\n",
    content_hash: "x".repeat(64),
    created_by: "user-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    submitted_at: null,
    submitted_by: null,
    locked_at: null,
    locked_by: null,
    ...overrides,
  };
}

describe("ScreenplayGovernanceTool", () => {
  beforeEach(() => {
    vi.mocked(api.screenplay.listVersions).mockReset();
    vi.mocked(api.screenplay.getVersion).mockReset();
    vi.mocked(api.screenplay.submit).mockReset();
    vi.mocked(api.screenplay.decide).mockReset();
    vi.mocked(api.screenplay.previewImpact).mockReset().mockResolvedValue({ affected_items: [] });
    vi.mocked(api.screenplay.listSuggestions).mockReset();
    vi.mocked(api.screenplay.listImpactAnalyses).mockReset();
  });

  it("lists versions with their status and a canonical badge", async () => {
    vi.mocked(api.screenplay.listVersions).mockResolvedValue([
      makeVersion({ id: "v1", version_number: 1, status: "approved_locked", is_production_canonical: true }) as never,
    ]);
    renderTool();
    expect(await screen.findByText("v1")).toBeInTheDocument();
    expect(screen.getByText("canonical")).toBeInTheDocument();
  });

  it("edits a draft version and submits it for review with a justification", async () => {
    const draft = makeVersion({ id: "v2", version_number: 2, status: "draft" });
    vi.mocked(api.screenplay.listVersions).mockResolvedValue([draft as never]);
    vi.mocked(api.screenplay.getVersion).mockResolvedValue(draft as never);
    vi.mocked(api.screenplay.updateVersion).mockResolvedValue({ ...draft, content_text: "new text" } as never);
    vi.mocked(api.screenplay.submit).mockResolvedValue({ ...draft, status: "in_review" } as never);

    renderTool();
    await userEvent.click(await screen.findByRole("button", { name: "Edit & submit" }));

    const textarea = await screen.findByLabelText("Screenplay text");
    await userEvent.clear(textarea);
    await userEvent.type(textarea, "new text");
    await userEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(api.screenplay.updateVersion).toHaveBeenCalledWith("prj-1", "v2", { content_text: "new text" });

    await userEvent.type(screen.getByLabelText(/Justification/), "Tightened the dialogue.");
    await userEvent.click(screen.getByRole("button", { name: "Submit for management review" }));
    expect(api.screenplay.submit).toHaveBeenCalledWith("prj-1", "v2", "Tightened the dialogue.");
  });

  it("shows approve/reject/request-changes actions for an in-review version and decides", async () => {
    const inReview = makeVersion({ id: "v3", version_number: 3, status: "in_review" });
    vi.mocked(api.screenplay.listVersions).mockResolvedValue([inReview as never]);
    vi.mocked(api.screenplay.decide).mockResolvedValue({
      approval_id: "approval-1",
      decision: "approved",
      version_status: "approved_locked",
      is_canonical: true,
    });

    renderTool();
    await userEvent.click(await screen.findByRole("button", { name: "Approve & lock" }));
    expect(api.screenplay.decide).toHaveBeenCalledWith("prj-1", "v3", { decision: "approved", notes: null });
  });
});
