import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

const TERMINAL_STATUSES = new Set(["awaiting_approval", "completed", "rejected", "failed"]);

/** Polls a workflow run until it leaves queued/running (packages/domain/enums.py
 * WorkflowStatus). Triggers are async by default (C6): the worker process picks the run
 * up from the outbox on its own schedule, so the UI's only way to know it progressed is
 * to keep asking. Polling stops itself once the run reaches a terminal status -- there is
 * nothing left to wait for. */
export function useWorkflowRun(runId: string | null) {
  return useQuery({
    queryKey: ["workflow-run", runId],
    queryFn: () => api.workflowRuns.get(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.has(status)) return false;
      return 2000;
    },
  });
}

export function isWorkflowRunTerminal(status: string): boolean {
  return TERMINAL_STATUSES.has(status);
}
