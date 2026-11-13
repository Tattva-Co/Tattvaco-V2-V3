import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CharacterStudioTool } from "../../../src/components/tools/CharacterStudioTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      projects: { ...actual.api.projects, characters: vi.fn(), scenes: vi.fn() },
      characters: {
        ...actual.api.characters,
        get: vi.fn(),
        listVersions: vi.fn(),
        listFacialReferences: vi.fn(),
        listStates: vi.fn(),
      },
      measurements: { ...actual.api.measurements, history: vi.fn() },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CharacterStudioTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

describe("CharacterStudioTool", () => {
  beforeEach(() => {
    vi.mocked(api.characters.get).mockReset();
    vi.mocked(api.characters.listVersions).mockReset();
  });

  it("prompts to run Script Intelligence first when there are no characters", async () => {
    vi.mocked(api.projects.characters).mockResolvedValue([]);
    renderTool();
    expect(await screen.findByText(/No canonical characters yet/)).toBeInTheDocument();
  });

  it("shows a character's profile once selected, with no approved version yet", async () => {
    vi.mocked(api.projects.characters).mockResolvedValue([
      { id: "char-1", project_id: "prj-1", organization_id: "org-1", canonical_name: "Vikram", aliases: ["Vikram"], project_version: 2, created_at: "2026-01-01T00:00:00Z" } as never,
    ]);
    vi.mocked(api.characters.get).mockResolvedValue({ id: "char-1", canonical_name: "Vikram", aliases: ["Vikram"], performer_id: null, current_version: null });
    vi.mocked(api.characters.listVersions).mockResolvedValue([]);

    renderTool();
    await userEvent.selectOptions(await screen.findByLabelText("Character"), "char-1");

    expect(await screen.findByText("No approved version yet.")).toBeInTheDocument();
  });
});
