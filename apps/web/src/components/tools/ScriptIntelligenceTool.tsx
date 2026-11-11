import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAssets } from "../../hooks/useAssets";
import { api } from "../../api/client";
import { describeError } from "../../lib/describeError";

/** Maps to JRN-02.2 (Script Intelligence): triggers the G-01 graph, which parses the
 * screenplay into scene/character/location candidates. Async by default (C6) -- this
 * only queues the run; `onRunStarted` tracks it in the task tray, which polls until a
 * human review gate opens. */
export function ScriptIntelligenceTool({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const assets = useAssets(projectId);
  // The server refuses a quarantined asset outright (AssetNotReadyError); only offering
  // 'clean' ones here means the dropdown never leads to a guaranteed-to-fail submit (in
  // practice every asset is clean by the time this list renders, since the no-op scanner
  // runs synchronously at upload -- this still future-proofs for a real, slower scanner).
  const cleanAssets = assets.data?.filter((a) => a.scan_status === "clean") ?? [];
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const trigger = useMutation({
    mutationFn: (assetId: string) => api.workflows.triggerScriptIntelligence(projectId, assetId),
    onSuccess: (result, assetId) => {
      const asset = cleanAssets.find((a) => a.id === assetId);
      onRunStarted(result.workflow_run_id, `Script Intelligence: ${asset?.filename ?? "screenplay"}`);
    },
  });

  if (assets.isLoading) return <div className="state-panel">Loading script assets…</div>;

  if (cleanAssets.length === 0) {
    return (
      <div className="state-panel">
        {assets.data && assets.data.length > 0
          ? "No scanned-clean script asset yet. Check the Assets tool."
          : "Upload a script asset first, under the Assets tool."}
      </div>
    );
  }

  return (
    <div>
      <p className="sub-desc" style={{ marginBottom: 14 }}>
        Parses the screenplay, segments scenes, and extracts characters and locations into candidate review. Run it,
        then open the Review tool once it reaches the approval gate.
      </p>
      <div className="tool-form">
        <label htmlFor="script-asset-select">Script asset</label>
        <select id="script-asset-select" value={selectedAssetId} onChange={(e) => setSelectedAssetId(e.target.value)}>
          <option value="">Select a script asset…</option>
          {cleanAssets.map((a) => (
            <option key={a.id} value={a.id}>
              {a.filename}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn primary"
          disabled={!selectedAssetId || trigger.isPending}
          onClick={() => trigger.mutate(selectedAssetId)}
        >
          {trigger.isPending ? "Starting…" : "Run Script Intelligence"}
        </button>
      </div>
      {trigger.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11, marginTop: 10 }}>
          {describeError(trigger.error)}
        </p>
      )}
      {trigger.isSuccess && (
        <p style={{ color: "var(--green)", fontSize: 11, marginTop: 10 }}>
          Started -- watch the task tray for progress.
        </p>
      )}
    </div>
  );
}
