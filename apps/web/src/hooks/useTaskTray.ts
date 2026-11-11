import { useCallback, useState } from "react";

export interface TrackedTask {
  runId: string;
  label: string;
  startedAt: number;
}

/** In-memory only (not persisted): a tray entry exists for the lifetime of the browser
 * tab, same as the task the user just started. Lives at ProjectWorkspacePage level so it
 * survives opening and closing individual Studio Tool panels. */
export function useTaskTray() {
  const [tasks, setTasks] = useState<TrackedTask[]>([]);

  const trackRun = useCallback((runId: string, label: string) => {
    setTasks((prev) => (prev.some((t) => t.runId === runId) ? prev : [...prev, { runId, label, startedAt: Date.now() }]));
  }, []);

  const dismiss = useCallback((runId: string) => {
    setTasks((prev) => prev.filter((t) => t.runId !== runId));
  }, []);

  return { tasks, trackRun, dismiss };
}
