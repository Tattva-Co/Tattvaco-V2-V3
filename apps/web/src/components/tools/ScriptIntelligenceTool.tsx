import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAssets } from "../../hooks/useAssets";
import { useImportScreenplayVersion, useScreenplayVersions } from "../../hooks/useScreenplay";
import { api } from "../../api/client";
import { describeError } from "../../lib/describeError";

/** Maps to JRN-02.2 (Script Intelligence): triggers the G-01 graph, which parses the
 * screenplay into scene/character/location candidates. D2 (TFD-SCR-004): WF-01 reads a
 * specific screenplay_version, never an asset directly -- import a version here first
 * (or reuse an existing one), then run against it. Async by default (C6) -- this only
 * queues the run; `onRunStarted` tracks it in the task tray, which polls until a human
 * review gate opens. */
export function ScriptIntelligenceTool({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const assets = useAssets(projectId);
  const versions = useScreenplayVersions(projectId);
  const importVersion = useImportScreenplayVersion(projectId);
  // The server refuses a quarantined asset outright (AssetNotReadyError); only offering
  // 'clean' ones here means the dropdown never leads to a guaranteed-to-fail submit (in
  // practice every asset is clean by the time this list renders, since the no-op scanner
  // runs synchronously at upload -- this still future-proofs for a real, slower scanner).
  const cleanAssets = assets.data?.filter((a) => a.scan_status === "clean") ?? [];
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");

  const trigger = useMutation({
    mutationFn: (versionId: string) => api.workflows.triggerScriptIntelligence(projectId, versionId),
    onSuccess: (result, versionId) => {
      const version = versions.data?.find((v) => v.id === versionId);
      onRunStarted(result.workflow_run_id, `Script Intelligence: v${version?.version_number ?? "?"}`);
    },
  });

  if (assets.isLoading || versions.isLoading) return <div className="state-panel">Loading…</div>;

  const versionList = versions.data ?? [];

  if (versionList.length === 0 && cleanAssets.length === 0) {
    return <div className="state-panel">Upload a script asset first, under the Assets tool.</div>;
  }

  return (
    <div>
      <p className="sub-desc" style={{ marginBottom: 14 }}>
        Parses a screenplay version, segments scenes, and extracts characters and locations into candidate review.
        Run it, then open the Review tool once it reaches the approval gate.
      </p>

      {cleanAssets.length > 0 && (
        <div className="tool-form" style={{ marginBottom: 16 }}>
          <label htmlFor="script-asset-select">Import a new screenplay version from an asset</label>
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
            className="btn small"
            disabled={!selectedAssetId || importVersion.isPending}
            onClick={() =>
              importVersion.mutate(
                { source_asset_id: selectedAssetId },
                { onSuccess: (v) => setSelectedVersionId(v.id) }
              )
            }
          >
            {importVersion.isPending ? "Importing…" : "Import as screenplay version"}
          </button>
          {importVersion.isError && (
            <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
              {describeError(importVersion.error)}
            </p>
          )}
        </div>
      )}

      {versionList.length === 0 ? (
        <div className="state-panel">No screenplay versions yet -- import one above.</div>
      ) : (
        <div className="tool-form">
          <label htmlFor="version-select">Screenplay version</label>
          <select id="version-select" value={selectedVersionId} onChange={(e) => setSelectedVersionId(e.target.value)}>
            <option value="">Select a screenplay version…</option>
            {versionList.map((v) => (
              <option key={v.id} value={v.id}>
                v{v.version_number} ({v.status}
                {v.is_production_canonical ? ", canonical" : ""})
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn primary"
            disabled={!selectedVersionId || trigger.isPending}
            onClick={() => trigger.mutate(selectedVersionId)}
          >
            {trigger.isPending ? "Starting…" : "Run Script Intelligence"}
          </button>
        </div>
      )}

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
