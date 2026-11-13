import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CinematographyTool } from "../../../src/components/tools/CinematographyTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      cinematography: {
        ...actual.api.cinematography,
        listCameraProfiles: vi.fn(),
        listLensProfiles: vi.fn(),
        listLightingProfiles: vi.fn(),
        getCurrentBible: vi.fn(),
        listBibleVersions: vi.fn(),
        listRecommendations: vi.fn(),
        requestRecommendation: vi.fn(),
      },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CinematographyTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

describe("CinematographyTool", () => {
  beforeEach(() => {
    vi.mocked(api.cinematography.listCameraProfiles).mockResolvedValue([]);
    vi.mocked(api.cinematography.listLensProfiles).mockResolvedValue([]);
    vi.mocked(api.cinematography.listLightingProfiles).mockResolvedValue([]);
    vi.mocked(api.cinematography.getCurrentBible).mockResolvedValue(null);
    vi.mocked(api.cinematography.listBibleVersions).mockResolvedValue([]);
    vi.mocked(api.cinematography.listRecommendations).mockResolvedValue([]);
  });

  it("shows no approved bible yet on the Cinematography Bible tab", async () => {
    renderTool();
    expect(await screen.findByText("No approved Cinematography Bible yet.")).toBeInTheDocument();
  });

  it("requests a recommendation and shows every required field", async () => {
    vi.mocked(api.cinematography.requestRecommendation).mockResolvedValue({
      id: "rec-1",
      project_id: "prj-1",
      intent_text: "warrior's first appearance at sunset, powerful, wide, epic",
      recommendation: {
        shot_type: { value: "wide shot", rationale: "wide cue", metadata_origin: "recommended" },
        lighting: { value: "golden-hour backlight", rationale: "sunset cue", metadata_origin: "recommended" },
      },
      overrides: {},
      generator_mode: "deterministic",
      created_by: "user-1",
      created_at: "2026-01-01T00:00:00Z",
    });
    vi.mocked(api.cinematography.listRecommendations).mockResolvedValueOnce([]).mockResolvedValue([
      {
        id: "rec-1",
        project_id: "prj-1",
        intent_text: "warrior's first appearance at sunset, powerful, wide, epic",
        recommendation: {
          shot_type: { value: "wide shot", rationale: "wide cue", metadata_origin: "recommended" },
          lighting: { value: "golden-hour backlight", rationale: "sunset cue", metadata_origin: "recommended" },
        },
        overrides: {},
        generator_mode: "deterministic",
        created_by: "user-1",
        created_at: "2026-01-01T00:00:00Z",
      },
    ]);

    renderTool();
    await userEvent.click(await screen.findByRole("tab", { name: "Recommendations" }));
    await userEvent.type(await screen.findByLabelText("Shot intent"), "warrior's first appearance at sunset, powerful, wide, epic");
    await userEvent.click(screen.getByRole("button", { name: "Request recommendation" }));

    expect(await screen.findByText(/wide shot/)).toBeInTheDocument();
    expect(await screen.findByText(/golden-hour backlight/)).toBeInTheDocument();
  });
});
