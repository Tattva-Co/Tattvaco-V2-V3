import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScriptIntelligenceTool } from "../../../src/components/tools/ScriptIntelligenceTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      assets: { list: vi.fn(), upload: vi.fn() },
      workflows: { triggerScriptIntelligence: vi.fn() },
      screenplay: { ...actual.api.screenplay, listVersions: vi.fn(), importVersion: vi.fn() },
    },
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

describe("ScriptIntelligenceTool", () => {
  beforeEach(() => {
    vi.mocked(api.assets.list).mockReset();
    vi.mocked(api.screenplay.listVersions).mockReset();
    vi.mocked(api.screenplay.importVersion).mockReset();
    vi.mocked(api.workflows.triggerScriptIntelligence).mockReset();
  });

  it("prompts to upload when there are no assets and no versions at all", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([]);
    vi.mocked(api.screenplay.listVersions).mockResolvedValue([]);
    renderTool();
    expect(await screen.findByText(/Upload a script asset first/)).toBeInTheDocument();
  });

  it("imports a clean asset as a screenplay version, then runs Script Intelligence against it", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([
      makeAsset({ id: "asset-1", filename: "clean.fountain", scan_status: "clean" }) as never,
      makeAsset({ id: "asset-2", filename: "dirty.fountain", scan_status: "quarantined" }) as never,
    ]);
    vi.mocked(api.screenplay.listVersions).mockResolvedValue([]);
    vi.mocked(api.screenplay.importVersion).mockResolvedValue(makeVersion() as never);
    vi.mocked(api.workflows.triggerScriptIntelligence).mockResolvedValue({
      workflow_run_id: "run-1",
      status: "queued",
      approval_request_id: null,
      candidate_summary: {},
    });

    renderTool();

    const assetSelect = await screen.findByLabelText(/Import a new screenplay version/);
    expect(screen.queryByRole("option", { name: "dirty.fountain" })).not.toBeInTheDocument();
    await userEvent.selectOptions(assetSelect, "asset-1");
    await userEvent.click(screen.getByRole("button", { name: "Import as screenplay version" }));

    expect(api.screenplay.importVersion).toHaveBeenCalledWith("prj-1", { source_asset_id: "asset-1" });
  });

  it("triggers Script Intelligence against an existing screenplay version", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([]);
    vi.mocked(api.screenplay.listVersions).mockResolvedValue([makeVersion() as never]);
    vi.mocked(api.workflows.triggerScriptIntelligence).mockResolvedValue({
      workflow_run_id: "run-1",
      status: "queued",
      approval_request_id: null,
      candidate_summary: {},
    });
    const onRunStarted = vi.fn();
    renderTool(onRunStarted);

    const versionSelect = await screen.findByLabelText("Screenplay version");
    await userEvent.selectOptions(versionSelect, "version-1");
    await userEvent.click(screen.getByRole("button", { name: "Run Script Intelligence" }));

    expect(api.workflows.triggerScriptIntelligence).toHaveBeenCalledWith("prj-1", "version-1");
    expect(onRunStarted).toHaveBeenCalledWith("run-1", "Script Intelligence: v1");
  });
});
