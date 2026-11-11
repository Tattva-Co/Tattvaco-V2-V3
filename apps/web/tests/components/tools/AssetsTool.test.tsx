import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AssetsTool } from "../../../src/components/tools/AssetsTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return { ...actual, api: { ...actual.api, assets: { list: vi.fn(), upload: vi.fn() } } };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AssetsTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

function makeAsset(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "asset-1",
    project_id: "prj-1",
    filename: "chronicle.fountain",
    mime_type: "text/plain",
    size_bytes: 2048,
    checksum_sha256: "a".repeat(64),
    storage_path: "/data/storage/asset-1",
    asset_type: "script",
    is_original: true,
    uploaded_by: "user-1",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("AssetsTool", () => {
  beforeEach(() => {
    vi.mocked(api.assets.list).mockReset();
    vi.mocked(api.assets.upload).mockReset();
  });

  it("shows an empty state when no assets exist yet", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([]);
    renderTool();
    expect(await screen.findByText("No script assets uploaded yet.")).toBeInTheDocument();
  });

  it("lists existing assets with size and checksum", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([makeAsset() as never]);
    renderTool();
    expect(await screen.findByText("chronicle.fountain")).toBeInTheDocument();
    expect(screen.getByText(/2\.0 KB/)).toBeInTheDocument();
  });

  it("uploads the chosen file and refreshes the list", async () => {
    vi.mocked(api.assets.list).mockResolvedValue([]);
    vi.mocked(api.assets.upload).mockResolvedValue({
      asset_id: "asset-2",
      filename: "new.fountain",
      mime_type: "text/plain",
      size_bytes: 10,
      checksum_sha256: "b".repeat(64),
      storage_path: "/data/storage/asset-2",
    });
    renderTool();
    await screen.findByText("No script assets uploaded yet.");

    const file = new File(["INT. ROOM - DAY"], "new.fountain", { type: "text/plain" });
    const input = screen.getByLabelText("Choose a screenplay file") as HTMLInputElement;
    await userEvent.upload(input, file);

    const uploadButton = screen.getByRole("button", { name: "Upload & store" });
    expect(uploadButton).toBeEnabled();
    await userEvent.click(uploadButton);

    expect(api.assets.upload).toHaveBeenCalledWith("prj-1", file);
  });
});
