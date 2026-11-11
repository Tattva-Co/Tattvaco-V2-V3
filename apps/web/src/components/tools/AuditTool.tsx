import { useAuditLog } from "../../hooks/useAudit";
import { describeError } from "../../lib/describeError";

/** Cross-stage: the complete audit trail for a project (audit.read capability). */
export function AuditTool({ projectId }: { projectId: string }) {
  const log = useAuditLog(projectId);

  if (log.isLoading) return <div className="state-panel">Loading audit log…</div>;
  if (log.isError) {
    return (
      <div className="state-panel error" role="alert">
        {describeError(log.error)}
      </div>
    );
  }
  if (log.data?.length === 0) return <div className="state-panel">No audit events recorded yet.</div>;

  return (
    <div>
      {log.data?.map((event) => (
        <div key={event.id} className="tool-list-item">
          <h4>
            {event.action.toUpperCase()} &mdash; {event.target_type}
          </h4>
          <p className="meta">
            Actor {event.actor_id.slice(0, 8)} · {new Date(event.created_at).toLocaleString()}
          </p>
          {Object.keys(event.details).length > 0 && (
            <pre style={{ fontSize: 10, background: "#f4f5f7", padding: 8, borderRadius: 6, overflowX: "auto" }}>
              {JSON.stringify(event.details, null, 2)}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}
