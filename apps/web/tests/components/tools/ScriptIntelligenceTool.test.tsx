import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScriptIntelligenceTool } from "../../../src/components/tools/ScriptIntelligenceTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: { ...actual.api, assets: { list: vi.fn(), upload: vi.fn() }, workflows: { triggerScriptIntelligence: vi.fn() } },
  };
});

import { api } from "../../../src/api/client";

function renderTool(onRunStarted = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ScriptIntelligenceTool projectId="prj-1" onRunStarted={onRunStarted} />
    </QueryClientProvider>
  );
}

function makeAsset(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "asset-1",
    project_id: "prj-1",
    filename: "chronicle.fountain",
    mime_type: "text/plain",
    size_bytes: 100,
    checksum_sha256: "a".repeat(64),
    storage_path: "/x",
    asset_type: "script",
    is_original: true,
    uploaded_by: "user-1",
    scan_status: "clean",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("ScriptIntelligenceTool", () => {
  beforeEach(() => {
    vi.mocked(api.assets.list).mockReset();
    vi.mocked(api.workflows.triggerScriptIntelligence).mockReset();
  });

  it("prompts to upload when there are no assets at all", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([]);
    renderTool();
    expect(await screen.findByText(/Upload a script asset first/)).toBeInTheDocument();
  });

  it("excludes a quarantined asset from the selectable list, even though it exists", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([makeAsset({ scan_status: "quarantined" }) as never]);
    renderTool();
    expect(await screen.findByText(/No scanned-clean script asset yet/)).toBeInTheDocument();
  });

  it("offers only clean assets and triggers the workflow for the selected one", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([
      makeAsset({ id: "asset-1", filename: "clean.fountain", scan_status: "clean" }) as never,
      makeAsset({ id: "asset-2", filename: "dirty.fountain", scan_status: "quarantined" }) as never,
    ]);
    vi.mocked(api.workflows.triggerScriptIntelligence).mockResolvedValue({
      workflow_run_id: "run-1",
      status: "queued",
      approval_request_id: null,
      candidate_summary: {},
    });
    const onRunStarted = vi.fn();
    renderTool(onRunStarted);

    const select = await screen.findByLabelText("Script asset");
    expect(screen.queryByRole("option", { name: "dirty.fountain" })).not.toBeInTheDocument();
    await userEvent.selectOptions(select, "asset-1");
    await userEvent.click(screen.getByRole("button", { name: "Run Script Intelligence" }));

    expect(api.workflows.triggerScriptIntelligence).toHaveBeenCalledWith("prj-1", "asset-1");
    expect(onRunStarted).toHaveBeenCalledWith("run-1", "Script Intelligence: clean.fountain");
  });
});
