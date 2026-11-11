import type { TrackedTask } from "../hooks/useTaskTray";
import { isWorkflowRunTerminal, useWorkflowRun } from "../hooks/useWorkflowRun";

const STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  awaiting_approval: "Ready for review",
  completed: "Completed",
  rejected: "Rejected",
  failed: "Failed",
};

const STATUS_CLASS: Record<string, string> = {
  queued: "progress",
  running: "progress",
  awaiting_approval: "review",
  completed: "done",
  rejected: "changes",
  failed: "blocked",
};

function TaskTrayItem({
  task,
  onDismiss,
  onOpenReview,
}: {
  task: TrackedTask;
  onDismiss: () => void;
  onOpenReview: () => void;
}) {
  const run = useWorkflowRun(task.runId);
  const status = run.data?.status ?? "queued";
  const terminal = isWorkflowRunTerminal(status);

  return (
    <div className="task-tray-item">
      <div>
        <div className="task-tray-label">{task.label}</div>
        {status === "failed" && run.data?.error_message && (
          <div className="task-tray-error">{run.data.error_message}</div>
        )}
      </div>
      <span className={`status ${STATUS_CLASS[status] ?? ""}`.trim()}>{STATUS_LABEL[status] ?? status}</span>
      {status === "awaiting_approval" && (
        <button type="button" className="tiny-btn primary" onClick={onOpenReview}>
          Review
        </button>
      )}
      {terminal && (
        <button type="button" className="task-tray-dismiss" aria-label={`Dismiss ${task.label}`} onClick={onDismiss}>
          &times;
        </button>
      )}
    </div>
  );
}

export function TaskTray({
  tasks,
  onDismiss,
  onOpenReview,
}: {
  tasks: TrackedTask[];
  onDismiss: (runId: string) => void;
  onOpenReview: () => void;
}) {
  if (tasks.length === 0) return null;
  return (
    <div className="task-tray" role="status" aria-label="Background tasks">
      {tasks.map((task) => (
        <TaskTrayItem key={task.runId} task={task} onDismiss={() => onDismiss(task.runId)} onOpenReview={onOpenReview} />
      ))}
    </div>
  );
}
