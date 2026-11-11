import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useStoryboardPanels } from "../../hooks/useStoryboard";
import { describeError } from "../../lib/describeError";

const TABS = ["Sequence Board", "Generate"] as const;
type Tab = (typeof TABS)[number];

function BoardTab({ projectId }: { projectId: string }) {
  const panels = useStoryboardPanels(projectId);
  if (panels.isLoading) return <div className="state-panel">Loading storyboard panels…</div>;
  if (panels.isError) {
    return (
      <div className="state-panel error" role="alert">
        {describeError(panels.error)}
      </div>
    );
  }
  if (panels.data?.length === 0) {
    return <div className="state-panel">No canonical panels yet. Generate some from the Generate tab.</div>;
  }
  return (
    <div>
      {panels.data?.map((p) => (
        <div key={p.id} className="tool-list-item">
          <h4>
            Panel #{p.panel_number} · {p.shot_type.replace(/_/g, " ")}
          </h4>
          <p>{p.description}</p>
          {p.visual_notes && <p className="meta">Visual notes: {p.visual_notes}</p>}
          {p.dialogue_snippet && <p className="meta">"{p.dialogue_snippet}"</p>}
          <div className="meta">
            {p.scene_id ? `Scene-linked · ` : "Sequence · "}
            {p.aspect_ratio} · v{p.project_version}
          </div>
        </div>
      ))}
    </div>
  );
}

function GenerateTab({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const [brief, setBrief] = useState("");
  const trigger = useMutation({
    mutationFn: () => api.workflows.triggerStoryboardIntelligence(projectId, brief.trim() || undefined),
    onSuccess: (result) => onRunStarted(result.workflow_run_id, "Storyboard intelligence"),
  });

  return (
    <div className="tool-form">
      <p className="sub-desc">
        Reads approved scenes and historical claims, derives shot framing, and proposes storyboard panels for
        review.
      </p>
      <label htmlFor="storyboard-brief">Director visual brief (optional)</label>
      <textarea id="storyboard-brief" value={brief} onChange={(e) => setBrief(e.target.value)} />
      <button type="button" className="btn primary" disabled={trigger.isPending} onClick={() => trigger.mutate()}>
        {trigger.isPending ? "Starting…" : "Run storyboard intelligence"}
      </button>
      {trigger.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
          {describeError(trigger.error)}
        </p>
      )}
      {trigger.isSuccess && <p style={{ color: "var(--green)", fontSize: 11 }}>Started -- watch the task tray.</p>}
    </div>
  );
}

/** Maps to JRN-06.5 (Storyboard & shot planning). */
export function StoryboardTool({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("Sequence Board");
  return (
    <div>
      <div className="tool-tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={`tool-tab${tab === t ? " active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Sequence Board" && <BoardTab projectId={projectId} />}
      {tab === "Generate" && <GenerateTab projectId={projectId} onRunStarted={onRunStarted} />}
    </div>
  );
}
