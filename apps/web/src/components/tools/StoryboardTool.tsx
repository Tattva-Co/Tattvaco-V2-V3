import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useAssets } from "../../hooks/useAssets";
import { useScenes } from "../../hooks/useFilmBible";
import {
  useCreateStoryboardMapping,
  useIngestStoryboard,
  useStoryboardMappings,
  useStoryboardPanels,
} from "../../hooks/useStoryboard";
import { describeError } from "../../lib/describeError";

const TABS = ["Sequence Board", "Generate", "Ingest PDF", "Scene Mapping"] as const;
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

function IngestTab({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const assets = useAssets(projectId);
  const ingest = useIngestStoryboard(projectId);
  const [assetId, setAssetId] = useState("");
  const cleanAssets = assets.data?.filter((a) => a.scan_status === "clean") ?? [];

  return (
    <div className="tool-form">
      <p className="sub-desc">
        Ingest a scanned storyboard PDF -- each page becomes a panel candidate with a
        crop image and a page locator, ready for review (TFD-SB-001).
      </p>
      <label htmlFor="ingest-asset-select">Storyboard PDF asset</label>
      <select id="ingest-asset-select" value={assetId} onChange={(e) => setAssetId(e.target.value)}>
        <option value="">Select an asset…</option>
        {cleanAssets.map((a) => (
          <option key={a.id} value={a.id}>
            {a.filename}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="btn primary"
        disabled={!assetId || ingest.isPending}
        onClick={() =>
          ingest.mutate(
            { source_asset_id: assetId },
            { onSuccess: (run) => onRunStarted(run.id, "Storyboard ingestion") }
          )
        }
      >
        {ingest.isPending ? "Ingesting…" : "Ingest PDF"}
      </button>
      {ingest.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
          {describeError(ingest.error)}
        </p>
      )}
      {ingest.isSuccess && (
        <p style={{ color: "var(--green)", fontSize: 11 }}>
          Ingested {ingest.data.output_refs.panel_count as number} page(s) -- review in Candidate Review.
        </p>
      )}
    </div>
  );
}

function MappingTab({ projectId }: { projectId: string }) {
  const panels = useStoryboardPanels(projectId);
  const scenes = useScenes(projectId);
  const mappings = useStoryboardMappings(projectId);
  const createMapping = useCreateStoryboardMapping(projectId);
  const [panelId, setPanelId] = useState("");
  const [sceneId, setSceneId] = useState("");

  return (
    <div>
      <p className="sub-desc" style={{ marginBottom: 14 }}>
        A panel can map to more than one scene (TFD-SB-003).
      </p>
      <div className="tool-form" style={{ marginBottom: 16 }}>
        <label>Panel</label>
        <select value={panelId} onChange={(e) => setPanelId(e.target.value)}>
          <option value="">Select a panel…</option>
          {panels.data?.map((p) => (
            <option key={p.id} value={p.id}>
              Panel #{p.panel_number}
            </option>
          ))}
        </select>
        <label>Scene</label>
        <select value={sceneId} onChange={(e) => setSceneId(e.target.value)}>
          <option value="">Select a scene…</option>
          {scenes.data?.map((s) => (
            <option key={s.id} value={s.id}>
              Scene {s.scene_number}: {s.heading}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn small"
          disabled={!panelId || !sceneId || createMapping.isPending}
          onClick={() => createMapping.mutate({ panel_id: panelId, scene_id: sceneId })}
        >
          Map panel to scene
        </button>
        {createMapping.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(createMapping.error)}
          </p>
        )}
      </div>
      {mappings.data?.length === 0 && <div className="state-panel">No mappings yet.</div>}
      {mappings.data?.map((m) => {
        const panel = panels.data?.find((p) => p.id === m.panel_id);
        const scene = scenes.data?.find((s) => s.id === m.scene_id);
        return (
          <div key={m.id} className="tool-list-item">
            <p>
              Panel #{panel?.panel_number ?? m.panel_id} -&gt; {scene ? `Scene ${scene.scene_number}: ${scene.heading}` : m.scene_id}
            </p>
          </div>
        );
      })}
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
      {tab === "Ingest PDF" && <IngestTab projectId={projectId} onRunStarted={onRunStarted} />}
      {tab === "Scene Mapping" && <MappingTab projectId={projectId} />}
    </div>
  );
}
