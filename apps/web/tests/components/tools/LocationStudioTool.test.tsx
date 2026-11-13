import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LocationStudioTool } from "../../../src/components/tools/LocationStudioTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      projects: { ...actual.api.projects, locations: vi.fn(), scenes: vi.fn() },
      locations: { ...actual.api.locations, get: vi.fn(), listVersions: vi.fn() },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <LocationStudioTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

describe("LocationStudioTool", () => {
  beforeEach(() => {
    vi.mocked(api.locations.get).mockReset();
  });

  it("prompts to run Script Intelligence first when there are no locations", async () => {
    vi.mocked(api.projects.locations).mockResolvedValue([]);
    renderTool();
    expect(await screen.findByText(/No canonical locations yet/)).toBeInTheDocument();
  });

  it("shows a location's profile once selected, with no approved version yet", async () => {
    vi.mocked(api.projects.locations).mockResolvedValue([
      { id: "loc-1", project_id: "prj-1", organization_id: "org-1", canonical_name: "Himalayan Pass", aliases: ["Himalayan Pass"], project_version: 2, created_at: "2026-01-01T00:00:00Z" } as never,
    ]);
    vi.mocked(api.locations.get).mockResolvedValue({ id: "loc-1", canonical_name: "Himalayan Pass", aliases: ["Himalayan Pass"], current_version: null });
    vi.mocked(api.locations.listVersions).mockResolvedValue([]);

    renderTool();
    await userEvent.selectOptions(await screen.findByLabelText("Location"), "loc-1");

    expect(await screen.findByText("No approved version yet.")).toBeInTheDocument();
  });
});
