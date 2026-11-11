import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TaskTray } from "../../src/components/TaskTray";

vi.mock("../../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../src/api/client")>();
  return { ...actual, api: { ...actual.api, workflowRuns: { get: vi.fn() } } };
});

import { api } from "../../src/api/client";

function renderTray(tasks: { runId: string; label: string; startedAt: number }[], onOpenReview = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <TaskTray tasks={tasks} onDismiss={vi.fn()} onOpenReview={onOpenReview} />
    </QueryClientProvider>
  );
}

function makeRun(overrides: Partial<{ status: string; error_message: string | null }> = {}) {
  return {
    id: "run-1",
    graph_id: "script_intelligence",
    graph_version: "v1",
    project_id: "prj-1",
    status: "queued",
    expected_project_version: 1,
    input_asset_ids: [],
    output_refs: {},
    error_message: null,
    generator_mode: "deterministic",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("TaskTray", () => {
  beforeEach(() => {
    vi.mocked(api.workflowRuns.get).mockReset();
  });

  it("renders nothing when there are no tracked tasks", () => {
    const { container } = renderTray([]);
    expect(container.firstChild).toBeNull();
  });

  it("shows a queued task with no dismiss button yet", async () => {
    vi.mocked(api.workflowRuns.get).mockResolvedValue(makeRun({ status: "queued" }));
    renderTray([{ runId: "run-1", label: "Script Intelligence: script.fountain", startedAt: Date.now() }]);

    expect(await screen.findByText("Script Intelligence: script.fountain")).toBeInTheDocument();
    expect(await screen.findByText("Queued")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Dismiss/ })).not.toBeInTheDocument();
  });

  it("offers a Review action once the run reaches awaiting_approval, and calls onOpenReview", async () => {
    vi.mocked(api.workflowRuns.get).mockResolvedValue(makeRun({ status: "awaiting_approval" }));
    const onOpenReview = vi.fn();
    renderTray([{ runId: "run-1", label: "Historical research: Sisupalgarh", startedAt: Date.now() }], onOpenReview);

    const reviewButton = await screen.findByRole("button", { name: "Review" });
    await userEvent.click(reviewButton);
    expect(onOpenReview).toHaveBeenCalledTimes(1);
  });

  it("shows a dismiss button and the error message once a run fails", async () => {
    vi.mocked(api.workflowRuns.get).mockResolvedValue(
      makeRun({ status: "failed", error_message: "The model gateway timed out." })
    );
    renderTray([{ runId: "run-1", label: "Film Bible synthesis", startedAt: Date.now() }]);

    expect(await screen.findByText("Failed")).toBeInTheDocument();
    expect(await screen.findByText("The model gateway timed out.")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Dismiss/ })).toBeInTheDocument();
  });
});
