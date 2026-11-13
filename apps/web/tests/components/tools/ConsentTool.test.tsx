import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConsentTool } from "../../../src/components/tools/ConsentTool";
import { ApiError } from "../../../src/api/client";

vi.mock("../../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      performers: { ...actual.api.performers, list: vi.fn(), create: vi.fn() },
      voiceProfiles: { ...actual.api.voiceProfiles, list: vi.fn() },
    },
  };
});

import { api } from "../../../src/api/client";

function renderTool() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ConsentTool projectId="prj-1" />
    </QueryClientProvider>
  );
}

describe("ConsentTool", () => {
  beforeEach(() => {
    vi.mocked(api.performers.list).mockReset();
    vi.mocked(api.performers.create).mockReset();
  });

  it("shows the policy_pending error when creating a performer before Legal approves the policy", async () => {
    vi.mocked(api.performers.list).mockResolvedValue([]);
    vi.mocked(api.performers.create).mockRejectedValue(new ApiError(403, "PolicyPendingError", "policy_pending"));

    renderTool();
    await userEvent.type(await screen.findByLabelText("Display name"), "Arjun Rao");
    await userEvent.click(screen.getByRole("button", { name: "Register performer" }));

    expect(await screen.findByText(/policy_pending/)).toBeInTheDocument();
  });

  it("lists registered performers", async () => {
    vi.mocked(api.performers.list).mockResolvedValue([
      { id: "perf-1", organization_id: "org-1", display_name: "Arjun Rao", notes: null, created_by: "user-1", created_at: "2026-01-01T00:00:00Z" },
    ]);

    renderTool();
    expect(await screen.findByRole("option", { name: "Arjun Rao" })).toBeInTheDocument();
  });
});
