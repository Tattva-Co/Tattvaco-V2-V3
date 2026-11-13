import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StoryboardTool } from "../../../src/components/tools/StoryboardTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      assets: { ...actual.api.assets, list: vi.fn() },
      projects: { ...actual.api.projects, scenes: vi.fn() },
      storyboard: { ...actual.api.storyboard, panels: vi.fn(), ingest: vi.fn(), listMappings: vi.fn(), createMapping: vi.fn() },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool(onRunStarted = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <StoryboardTool projectId="prj-1" onRunStarted={onRunStarted} />
    </QueryClientProvider>
  );
}

describe("StoryboardTool: ingestion and scene mapping", () => {
  beforeEach(() => {
    vi.mocked(api.storyboard.panels).mockResolvedValue([]);
    vi.mocked(api.assets.list).mockResolvedValue([
      { id: "asset-1", project_id: "prj-1", filename: "board.pdf", mime_type: "application/pdf", size_bytes: 10, checksum_sha256: "a".repeat(64), storage_path: "/x", asset_type: "document", is_original: true, uploaded_by: "user-1", scan_status: "clean", created_at: "2026-01-01T00:00:00Z" } as never,
    ]);
    vi.mocked(api.projects.scenes).mockResolvedValue([]);
    vi.mocked(api.storyboard.listMappings).mockResolvedValue([]);
  });

  it("ingests a PDF asset and reports the panel count", async () => {
    const onRunStarted = vi.fn();
    vi.mocked(api.storyboard.ingest).mockResolvedValue({
      id: "run-1",
      graph_id: "storyboard_ingestion",
      graph_version: "1.0",
      project_id: "prj-1",
      status: "awaiting_approval",
      expected_project_version: 1,
      input_asset_ids: ["asset-1"],
      output_refs: { panel_count: 3, page_errors: [] },
      error_message: null,
      generator_mode: "deterministic",
      screenplay_version_id: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    renderTool(onRunStarted);
    await userEvent.click(await screen.findByRole("tab", { name: "Ingest PDF" }));
    await userEvent.selectOptions(await screen.findByLabelText("Storyboard PDF asset"), "asset-1");
    await userEvent.click(screen.getByRole("button", { name: "Ingest PDF" }));

    expect(await screen.findByText(/Ingested 3 page\(s\)/)).toBeInTheDocument();
    expect(onRunStarted).toHaveBeenCalledWith("run-1", "Storyboard ingestion");
  });

  it("shows no mappings yet on the Scene Mapping tab", async () => {
    renderTool();
    await userEvent.click(await screen.findByRole("tab", { name: "Scene Mapping" }));
    expect(await screen.findByText("No mappings yet.")).toBeInTheDocument();
  });
});
