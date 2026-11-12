import { useProjectSummary } from "../../hooks/useProjects";
import { describeError } from "../../lib/describeError";

/** S-PRJ-01 Project Overview (TFD-PRJ-007): answers "where am I, what is understood,
 * what is unresolved, what needs me, what's next" from stored data only -- no
 * percentage or score here is derived from anything but a real query (AT-PRJ-007 #1).
 */
export function ProjectOverviewTool({ projectId }: { projectId: string }) {
  const summary = useProjectSummary(projectId);

  if (summary.isLoading) return <div className="state-panel">Loading project overview…</div>;
  if (summary.isError) {
    return (
      <div className="state-panel error" role="alert">
        {describeError(summary.error)}
      </div>
    );
  }
  const data = summary.data;
  if (!data) return null;

  const modeEntries = Object.entries(data.scene_count_by_effective_mode);

  return (
    <div>
      {data.next_action && (
        <div className="tool-list-item" style={{ borderLeft: "3px solid var(--gold)" }}>
          <h4>Next action</h4>
          <p>{data.next_action.title}</p>
          <p className="meta">{data.next_action.reason}</p>
        </div>
      )}

      <div className="tool-list-item">
        <h4>Screenplay</h4>
        <p className="meta">
          {data.canonical_screenplay_version !== null
            ? `Canonical version ${data.canonical_screenplay_version}`
            : "No screenplay version is locked yet"}{" "}
          ({data.screenplay_lock_state.replace(/_/g, " ")})
        </p>
        <p className="meta">Project version: v{data.project_version}</p>
      </div>

      <div className="tool-list-item">
        <h4>Scenes by production mode</h4>
        {modeEntries.length === 0 ? (
          <p className="meta">No canonical scenes yet.</p>
        ) : (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {modeEntries.map(([mode, count]) => (
              <span key={mode} className="tag amber">
                {mode.replace(/_/g, " ")}: {count}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="tool-list-item">
        <h4>Pending approvals</h4>
        <p className="meta">{data.pending_approvals_count} awaiting a decision</p>
      </div>

      <div className="tool-list-item">
        <h4>Running tasks</h4>
        {data.running_tasks.length === 0 ? (
          <p className="meta">Nothing running right now.</p>
        ) : (
          data.running_tasks.map((t) => (
            <p key={t.workflow_run_id} className="meta">
              {t.graph_id} · {t.status}
            </p>
          ))
        )}
      </div>

      <div className="tool-list-item">
        <h4>Recent changes</h4>
        {data.recent_changes.length === 0 ? (
          <p className="meta">No activity yet.</p>
        ) : (
          data.recent_changes.map((c, i) => (
            <p key={i} className="meta">
              {c.action.replace(/_/g, " ")} · {new Date(c.created_at).toLocaleString()}
            </p>
          ))
        )}
      </div>

      <div className="tool-list-item">
        <h4>Continuity findings</h4>
        <p className="meta">
          {data.unresolved_high_severity_findings_count} unresolved high-severity findings (continuity checking
          is not built yet)
        </p>
      </div>
    </div>
  );
}
