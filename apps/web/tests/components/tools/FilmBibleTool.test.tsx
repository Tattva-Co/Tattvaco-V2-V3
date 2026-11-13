import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FilmBibleTool } from "../../../src/components/tools/FilmBibleTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      filmBible: { rules: { list: vi.fn(), create: vi.fn() } },
      projects: {
        ...actual.api.projects,
        scenes: vi.fn(),
        entities: vi.fn(),
        dialogueSegments: vi.fn(),
        characters: vi.fn(),
        locations: vi.fn(),
        versions: vi.fn(),
      },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <FilmBibleTool projectId="prj-1" onRunStarted={vi.fn()} />
    </QueryClientProvider>
  );
}

describe("FilmBibleTool: Story Intelligence v2 tabs", () => {
  beforeEach(() => {
    vi.mocked(api.filmBible.rules.list).mockResolvedValue([]);
    vi.mocked(api.projects.versions).mockResolvedValue([]);
    vi.mocked(api.projects.scenes).mockResolvedValue([
      {
        id: "scene-1",
        workflow_run_id: "run-1",
        scene_number: 1,
        heading: "EXT. HIMALAYAN PASS - DAWN",
        setting: "EXT",
        location_name: "Himalayan Pass",
        time_of_day: "DAWN",
        summary: "",
        characters_present: ["Vikram"],
        status: "approved",
        generator_mode: "deterministic",
        project_version: 2,
      } as never,
    ]);
    vi.mocked(api.projects.entities).mockResolvedValue([]);
  });

  it("groups dialogue segments by their scene, shown verbatim", async () => {
    vi.mocked(api.projects.dialogueSegments).mockResolvedValue([
      {
        id: "dlg-1",
        scene_id: "scene-1",
        screenplay_version_id: null,
        character_id: "char-1",
        character_name: "Vikram",
        line_text: "The celestial alignment matches the scripture.",
        parenthetical: "quietly",
        order_in_scene: 1,
        source_locator: "Scene 1 (Line 7)",
        project_version: 2,
        created_at: "2026-01-01T00:00:00Z",
      } as never,
    ]);

    renderTool();
    await userEvent.click(await screen.findByRole("tab", { name: "Dialogue" }));

    expect(await screen.findByText("Scene 1: EXT. HIMALAYAN PASS - DAWN")).toBeInTheDocument();
    expect(screen.getByText("Vikram")).toBeInTheDocument();
    expect(screen.getByText(/The celestial alignment matches the scripture\./)).toBeInTheDocument();
    expect(screen.getByText("(quietly)")).toBeInTheDocument();
  });

  it("lists resolved characters with their aliases", async () => {
    vi.mocked(api.projects.characters).mockResolvedValue([
      { id: "char-1", canonical_name: "Vikram", aliases: ["Vikram"], project_version: 2, created_at: "2026-01-01T00:00:00Z" } as never,
    ]);

    renderTool();
    await userEvent.click(await screen.findByRole("tab", { name: "Characters" }));

    expect(await screen.findByText("Vikram")).toBeInTheDocument();
  });

  it("lists resolved locations with their aliases", async () => {
    vi.mocked(api.projects.locations).mockResolvedValue([
      {
        id: "loc-1",
        canonical_name: "Himalayan Pass",
        aliases: ["Himalayan Pass"],
        project_version: 2,
        created_at: "2026-01-01T00:00:00Z",
      } as never,
    ]);

    renderTool();
    await userEvent.click(await screen.findByRole("tab", { name: "Locations" }));

    expect(await screen.findByText("Himalayan Pass")).toBeInTheDocument();
  });
});
