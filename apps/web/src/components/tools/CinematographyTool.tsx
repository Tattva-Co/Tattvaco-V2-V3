import { useState } from "react";
import {
  useCameraProfiles,
  useCinematographyBibleVersions,
  useCinematographyRecommendations,
  useCreateCameraProfile,
  useCreateLensProfile,
  useCreateLightingProfile,
  useCurrentCinematographyBible,
  useDecideBibleVersion,
  useLensProfiles,
  useLightingProfiles,
  useOverrideRecommendation,
  useProposeBibleVersion,
  useRequestRecommendation,
} from "../../hooks/useCinematography";
import { describeError } from "../../lib/describeError";

const TABS = ["Cinematography Bible", "Recommendations"] as const;
type Tab = (typeof TABS)[number];

/** S-CIN-01 (JRN-06.1-06.4): camera/lens/lighting libraries, the versioned
 * Cinematography Bible, and AI shot-planning recommendations with override. */
export function CinematographyTool({ projectId }: { projectId: string }) {
  const [tab, setTab] = useState<Tab>("Cinematography Bible");
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
      {tab === "Cinematography Bible" && <BibleTab projectId={projectId} />}
      {tab === "Recommendations" && <RecommendationsTab projectId={projectId} />}
    </div>
  );
}

function BibleTab({ projectId }: { projectId: string }) {
  const cameraProfiles = useCameraProfiles(projectId);
  const lensProfiles = useLensProfiles(projectId);
  const lightingProfiles = useLightingProfiles(projectId);
  const current = useCurrentCinematographyBible(projectId);
  const versions = useCinematographyBibleVersions(projectId);
  const createCamera = useCreateCameraProfile(projectId);
  const createLens = useCreateLensProfile(projectId);
  const createLighting = useCreateLightingProfile(projectId);
  const propose = useProposeBibleVersion(projectId);
  const decide = useDecideBibleVersion(projectId);

  const [cameraName, setCameraName] = useState("");
  const [specKind, setSpecKind] = useState("physical");
  const [lensName, setLensName] = useState("");
  const [lightingName, setLightingName] = useState("");
  const [selectedCameraIds, setSelectedCameraIds] = useState<string[]>([]);
  const [selectedLensIds, setSelectedLensIds] = useState<string[]>([]);
  const [selectedLightingIds, setSelectedLightingIds] = useState<string[]>([]);
  const [palette, setPalette] = useState("");
  const [filmLook, setFilmLook] = useState("");

  const toggle = (list: string[], id: string) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  const draftVersions = (versions.data ?? []).filter((v) => v.status === "draft");

  return (
    <div>
      <h4>Current Cinematography Bible</h4>
      {current.data ? (
        <div className="tool-list-item">
          <p className="meta">v{current.data.version_number}</p>
          <p>Visual language: {JSON.stringify(current.data.visual_language)}</p>
        </div>
      ) : (
        <div className="state-panel">No approved Cinematography Bible yet.</div>
      )}

      {draftVersions.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <h4>Awaiting approval</h4>
          {draftVersions.map((v) => (
            <div key={v.id} className="tool-list-item">
              <p className="meta">v{v.version_number} (draft)</p>
              <button type="button" className="btn small" onClick={() => decide.mutate({ versionId: v.id, body: { decision: "approved" } })}>
                Approve
              </button>{" "}
              <button type="button" className="tiny-btn" onClick={() => decide.mutate({ versionId: v.id, body: { decision: "rejected" } })}>
                Reject
              </button>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <h4>Camera library</h4>
        {cameraProfiles.data?.map((c) => (
          <label key={c.id} style={{ display: "block" }}>
            <input
              type="checkbox"
              checked={selectedCameraIds.includes(c.id)}
              onChange={() => setSelectedCameraIds((prev) => toggle(prev, c.id))}
            />{" "}
            {c.name} ({c.spec_kind})
          </label>
        ))}
        <div className="tool-form" style={{ marginTop: 8 }}>
          <input value={cameraName} onChange={(e) => setCameraName(e.target.value)} placeholder="Camera name" aria-label="Camera name" />
          <select value={specKind} onChange={(e) => setSpecKind(e.target.value)} aria-label="Spec kind">
            <option value="physical">Physical</option>
            <option value="virtual">Virtual</option>
          </select>
          <button
            type="button"
            className="tiny-btn"
            disabled={!cameraName.trim()}
            onClick={() => createCamera.mutate({ name: cameraName.trim(), spec_kind: specKind }, { onSuccess: () => setCameraName("") })}
          >
            Add camera
          </button>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <h4>Lens library</h4>
        {lensProfiles.data?.map((l) => (
          <label key={l.id} style={{ display: "block" }}>
            <input
              type="checkbox"
              checked={selectedLensIds.includes(l.id)}
              onChange={() => setSelectedLensIds((prev) => toggle(prev, l.id))}
            />{" "}
            {l.name}
          </label>
        ))}
        <div className="tool-form" style={{ marginTop: 8 }}>
          <input value={lensName} onChange={(e) => setLensName(e.target.value)} placeholder="Lens name" aria-label="Lens name" />
          <button
            type="button"
            className="tiny-btn"
            disabled={!lensName.trim()}
            onClick={() => createLens.mutate({ name: lensName.trim() }, { onSuccess: () => setLensName("") })}
          >
            Add lens
          </button>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <h4>Lighting library</h4>
        {lightingProfiles.data?.map((l) => (
          <label key={l.id} style={{ display: "block" }}>
            <input
              type="checkbox"
              checked={selectedLightingIds.includes(l.id)}
              onChange={() => setSelectedLightingIds((prev) => toggle(prev, l.id))}
            />{" "}
            {l.name}
          </label>
        ))}
        <div className="tool-form" style={{ marginTop: 8 }}>
          <input
            value={lightingName}
            onChange={(e) => setLightingName(e.target.value)}
            placeholder="Lighting setup name"
            aria-label="Lighting setup name"
          />
          <button
            type="button"
            className="tiny-btn"
            disabled={!lightingName.trim()}
            onClick={() => createLighting.mutate({ name: lightingName.trim() }, { onSuccess: () => setLightingName("") })}
          >
            Add lighting setup
          </button>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <h4>Propose a new Bible version</h4>
        <div className="tool-form">
          <label>Visual language -- palette</label>
          <input value={palette} onChange={(e) => setPalette(e.target.value)} aria-label="Palette" />
          <label>Visual language -- film look</label>
          <input value={filmLook} onChange={(e) => setFilmLook(e.target.value)} aria-label="Film look" />
          <button
            type="button"
            className="btn primary"
            disabled={propose.isPending}
            onClick={() =>
              propose.mutate({
                camera_profile_ids: selectedCameraIds,
                lens_profile_ids: selectedLensIds,
                lighting_profile_ids: selectedLightingIds,
                visual_language: { palette, film_look: filmLook },
              })
            }
          >
            Submit for approval
          </button>
          {propose.isError && (
            <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
              {describeError(propose.error)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function RecommendationsTab({ projectId }: { projectId: string }) {
  const recommendations = useCinematographyRecommendations(projectId);
  const request = useRequestRecommendation(projectId);
  const override = useOverrideRecommendation(projectId);
  const [intent, setIntent] = useState("");

  return (
    <div>
      <p className="sub-desc" style={{ marginBottom: 14 }}>
        No recommended field is ever auto-applied -- the director reviews and may
        override any field, which is stored alongside the original recommendation.
      </p>
      <div className="tool-form" style={{ marginBottom: 16 }}>
        <label htmlFor="cin-intent">Shot intent</label>
        <textarea id="cin-intent" value={intent} onChange={(e) => setIntent(e.target.value)} />
        <button
          type="button"
          className="btn primary"
          disabled={!intent.trim() || request.isPending}
          onClick={() => request.mutate({ intent: intent.trim() }, { onSuccess: () => setIntent("") })}
        >
          {request.isPending ? "Thinking…" : "Request recommendation"}
        </button>
        {request.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(request.error)}
          </p>
        )}
      </div>

      {recommendations.data?.length === 0 && <div className="state-panel">No recommendations yet.</div>}
      {recommendations.data?.map((r) => (
        <div key={r.id} className="tool-list-item">
          <h4>"{r.intent_text}"</h4>
          {Object.entries(r.recommendation).map(([field, data]) => {
            const d = data as { value: string | string[]; rationale: string };
            const overridden = r.overrides[field] as { value: string } | undefined;
            return (
              <p key={field}>
                <strong>{field}</strong>: {overridden ? <s>{String(d.value)}</s> : String(d.value)}
                {overridden && <> -&gt; {String(overridden.value)} (overridden)</>}
                <br />
                <span className="meta">{d.rationale}</span>
                {!overridden && field !== "references" && (
                  <>
                    {" "}
                    <button
                      type="button"
                      className="tiny-btn"
                      onClick={() => {
                        const next = window.prompt(`Override ${field}:`, String(d.value));
                        if (next) override.mutate({ recommendationId: r.id, body: { field_name: field, value: next } });
                      }}
                    >
                      Override
                    </button>
                  </>
                )}
              </p>
            );
          })}
        </div>
      ))}
    </div>
  );
}
