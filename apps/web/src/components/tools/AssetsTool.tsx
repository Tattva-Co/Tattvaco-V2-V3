import { useRef, useState } from "react";
import { useAssets, useUploadAsset } from "../../hooks/useAssets";
import { describeError } from "../../lib/describeError";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Maps to JRN-02.1 (Import screenplay): upload screenplays into immutable storage. Every
 * asset is SHA-256 checksummed server-side (packages/services/assets.py) before any
 * workflow can read it. */
export function AssetsTool({ projectId }: { projectId: string }) {
  const assets = useAssets(projectId);
  const upload = useUploadAsset(projectId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  async function handleUpload() {
    if (!pendingFile) return;
    try {
      await upload.mutateAsync(pendingFile);
      setPendingFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch {
      // surfaced via upload.isError below
    }
  }

  return (
    <div>
      <p className="sub-desc" style={{ marginBottom: 14 }}>
        Upload screenplays (.fountain, .txt, .pdf) into private, immutable storage. Each file is verified with a
        SHA-256 digest before any workflow can read it.
      </p>

      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 18 }}>
        <input
          ref={inputRef}
          type="file"
          accept=".fountain,.txt,.pdf"
          aria-label="Choose a screenplay file"
          onChange={(e) => setPendingFile(e.target.files?.[0] ?? null)}
        />
        <button type="button" className="btn primary small" disabled={!pendingFile || upload.isPending} onClick={handleUpload}>
          {upload.isPending ? "Uploading…" : "Upload & store"}
        </button>
      </div>
      {upload.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11, marginBottom: 14 }}>
          {describeError(upload.error)}
        </p>
      )}

      <h3 style={{ fontSize: 12, margin: "0 0 10px" }}>Project assets</h3>
      {assets.isLoading && <div className="state-panel">Loading assets…</div>}
      {assets.isError && (
        <div className="state-panel error" role="alert">
          {describeError(assets.error)}
        </div>
      )}
      {assets.data && assets.data.length === 0 && <div className="state-panel">No script assets uploaded yet.</div>}
      {assets.data?.map((asset) => (
        <div key={asset.id} className="tool-list-item">
          <h4>{asset.filename}</h4>
          <p>
            {formatBytes(asset.size_bytes)} &middot; {asset.mime_type}
          </p>
          <div className="meta">
            SHA-256: {asset.checksum_sha256.slice(0, 16)}… &middot; Uploaded {new Date(asset.created_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}
