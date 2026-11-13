import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CostumePropsTool } from "../../../src/components/tools/CostumePropsTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      projects: { ...actual.api.projects, characters: vi.fn(), scenes: vi.fn() },
      costumes: { ...actual.api.costumes, list: vi.fn(), create: vi.fn() },
      props: { ...actual.api.props, list: vi.fn(), create: vi.fn() },
      continuityFindings: { ...actual.api.continuityFindings, list: vi.fn() },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CostumePropsTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

describe("CostumePropsTool", () => {
  beforeEach(() => {
    vi.mocked(api.projects.characters).mockResolvedValue([]);
    vi.mocked(api.projects.scenes).mockResolvedValue([]);
    vi.mocked(api.costumes.list).mockResolvedValue([]);
    vi.mocked(api.props.list).mockResolvedValue([]);
    vi.mocked(api.continuityFindings.list).mockResolvedValue([]);
  });

  it("shows no costumes yet on the Costumes tab", async () => {
    renderTool();
    expect(await screen.findByText("No costumes yet.")).toBeInTheDocument();
  });

  it("shows no continuity findings on that tab", async () => {
    renderTool();
    await userEvent.click(await screen.findByRole("tab", { name: "Continuity Findings" }));
    expect(await screen.findByText("No continuity findings.")).toBeInTheDocument();
  });

  it("lists registered props on the Props & Weapons tab", async () => {
    vi.mocked(api.props.list).mockResolvedValue([
      { id: "prop-1", project_id: "prj-1", organization_id: "org-1", name: "Vikram's Khanda", kind: "weapon", type: null, design: null, material: null, scale: null, owner_character_id: null, created_by: "user-1", created_at: "2026-01-01T00:00:00Z" },
    ]);
    renderTool();
    await userEvent.click(await screen.findByRole("tab", { name: "Props & Weapons" }));
    expect(await screen.findByRole("option", { name: "Vikram's Khanda (weapon)" })).toBeInTheDocument();
  });
});
