import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProjectMembersTool } from "../../../src/components/tools/ProjectMembersTool";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      members: { roleTemplates: vi.fn(), list: vi.fn(), add: vi.fn(), updateRole: vi.fn(), remove: vi.fn() },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectMembersTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

const ROLE_TEMPLATES = [
  { key: "project_owner", name: "Project Owner", capabilities: ["project.admin"] },
  { key: "viewer", name: "Viewer", capabilities: ["project.read"] },
];

const MEMBERS = [
  {
    user_id: "user-1",
    email: "owner@studio.example",
    full_name: "Owner Person",
    role_template_key: "project_owner",
    role_template_name: "Project Owner",
    capabilities: ["project.admin"],
  },
];

describe("ProjectMembersTool", () => {
  beforeEach(() => {
    vi.mocked(api.members.roleTemplates).mockReset().mockResolvedValue(ROLE_TEMPLATES);
    vi.mocked(api.members.list).mockReset().mockResolvedValue(MEMBERS);
    vi.mocked(api.members.add).mockReset();
    vi.mocked(api.members.remove).mockReset();
  });

  it("lists existing members with their role", async () => {
    renderTool();
    expect(await screen.findByText("Owner Person")).toBeInTheDocument();
    expect(screen.getByText("owner@studio.example")).toBeInTheDocument();
  });

  it("adds a new member by email with the selected role", async () => {
    vi.mocked(api.members.add).mockResolvedValue({
      user_id: "user-2",
      email: "new@studio.example",
      full_name: "New Person",
      role_template_key: "viewer",
      role_template_name: "Viewer",
      capabilities: ["project.read"],
    });
    renderTool();
    await screen.findByText("Owner Person");

    await userEvent.type(screen.getByLabelText(/Add an existing organization member/), "new@studio.example");
    await userEvent.click(screen.getByRole("button", { name: "Add member" }));

    expect(api.members.add).toHaveBeenCalledWith("prj-1", {
      email: "new@studio.example",
      role_template_key: "viewer",
    });
  });

  it("removes a member", async () => {
    renderTool();
    await userEvent.click(await screen.findByRole("button", { name: "Remove" }));
    expect(api.members.remove).toHaveBeenCalledWith("prj-1", "user-1");
  });
});
