import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectSettingsTool } from "../../../src/components/tools/ProjectSettingsTool";
import { makeProject } from "../../factories";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      projects: { ...actual.api.projects, update: vi.fn(), archive: vi.fn(), unarchive: vi.fn() },
      projectTemplates: { list: vi.fn() },
      outputProfiles: { list: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn() },
      episodes: { list: vi.fn(), create: vi.fn() },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool(overrides = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const project = makeProject(overrides);
  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectSettingsTool project={project} />
    </QueryClientProvider>
  );
}

describe("ProjectSettingsTool", () => {
  beforeEach(() => {
    vi.mocked(api.projectTemplates.list).mockReset().mockResolvedValue([]);
    vi.mocked(api.outputProfiles.list).mockReset().mockResolvedValue([]);
    vi.mocked(api.episodes.list).mockReset().mockResolvedValue([]);
    vi.mocked(api.projects.update).mockReset();
    vi.mocked(api.projects.archive).mockReset();
    vi.mocked(api.projects.unarchive).mockReset();
  });

  it("prefills the metadata form from the current project and saves an edited title", async () => {
    vi.mocked(api.projects.update).mockResolvedValue(makeProject({ title: "New Title" }));
    renderTool({ title: "Old Title" });

    const titleInput = screen.getByLabelText("Title") as HTMLInputElement;
    expect(titleInput.value).toBe("Old Title");

    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "New Title");
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));

    expect(api.projects.update).toHaveBeenCalledWith(
      "prj-1",
      expect.objectContaining({ title: "New Title" })
    );
  });

  it("archives an active project", async () => {
    vi.mocked(api.projects.archive).mockResolvedValue(makeProject({ status: "archived" }));
    renderTool({ status: "active" });

    await userEvent.click(await screen.findByRole("button", { name: "Archive project" }));
    expect(api.projects.archive).toHaveBeenCalledWith("prj-1");
  });

  it("offers to unarchive an already-archived project", async () => {
    renderTool({ status: "archived" });
    expect(await screen.findByRole("button", { name: "Unarchive project" })).toBeInTheDocument();
  });
});
