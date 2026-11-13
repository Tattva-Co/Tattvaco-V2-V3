import { useState } from "react";
import { useLocations, useScenes } from "../../hooks/useFilmBible";
import {
  useAdoptLocation,
  useCreateEnvironmentState,
  useDecideLocationVersion,
  useEnvironmentState,
  useLocationDetail,
  useLocationVersions,
  useProposeLocationVersion,
} from "../../hooks/useVisualWorld";
import { describeError } from "../../lib/describeError";

const TABS = ["Profile", "Environment States"] as const;
type Tab = (typeof TABS)[number];

const PROVENANCE_SOURCES = ["screenplay", "research_claim", "director", "ai_candidate", "performer_measurement", "scan"];
const PROVENANCE_STATUSES = ["estimated", "verified", "approved", "disputed"];

/** S-ENV-01 (JRN-05.2/05.3): location/environment profile versioning, the legacy
 * location link, and scene-level environment states. */
export function LocationStudioTool({ projectId }: { projectId: string }) {
  const locations = useLocations(projectId);
  const [locationId, setLocationId] = useState("");

  if (locations.isLoading) return <div className="state-panel">Loading locations…</div>;
  if (!locations.data || locations.data.length === 0) {
    return <div className="state-panel">No canonical locations yet -- run Script Intelligence first.</div>;
  }

  return (
    <div>
      <div className="tool-form" style={{ marginBottom: 14 }}>
        <label htmlFor="location-select">Location</label>
        <select id="location-select" value={locationId} onChange={(e) => setLocationId(e.target.value)}>
          <option value="">Select a location…</option>
          {locations.data.map((l) => (
            <option key={l.id} value={l.id}>
              {l.canonical_name}
            </option>
          ))}
        </select>
      </div>
      {locationId && <LocationDetail projectId={projectId} locationId={locationId} />}
    </div>
  );
}

function LocationDetail({ projectId, locationId }: { projectId: string; locationId: string }) {
  const [tab, setTab] = useState<Tab>("Profile");
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
      {tab === "Profile" && <ProfileTab projectId={projectId} locationId={locationId} />}
      {tab === "Environment States" && <EnvironmentStatesTab projectId={projectId} locationId={locationId} />}
    </div>
  );
}

function CharacteristicEditor({ onAdd }: { onAdd: (field: string, envelope: Record<string, unknown>) => void }) {
  const [field, setField] = useState("");
  const [value, setValue] = useState("");
  const [source, setSource] = useState(PROVENANCE_SOURCES[0]);
  const [status, setStatus] = useState(PROVENANCE_STATUSES[2]);

  return (
    <div className="tool-form" style={{ marginBottom: 12 }}>
      <label>Field name</label>
      <input
        value={field}
        onChange={(e) => setField(e.target.value)}
        placeholder="e.g. geography, architecture, period"
        aria-label="Field name"
      />
      <label>Value</label>
      <input value={value} onChange={(e) => setValue(e.target.value)} aria-label="Characteristic value" />
      <label>Source</label>
      <select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
        {PROVENANCE_SOURCES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <label>Status</label>
      <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
        {PROVENANCE_STATUSES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="btn small"
        disabled={!field.trim() || !value.trim()}
        onClick={() => {
          onAdd(field.trim(), { value, source, status, approved_by: null });
          setField("");
          setValue("");
        }}
      >
        Add characteristic to this edit
      </button>
    </div>
  );
}

function ProfileTab({ projectId, locationId }: { projectId: string; locationId: string }) {
  const detail = useLocationDetail(projectId, locationId);
  const versions = useLocationVersions(projectId, locationId);
  const propose = useProposeLocationVersion(projectId, locationId);
  const decide = useDecideLocationVersion(projectId, locationId);
  const adopt = useAdoptLocation(projectId);
  const [pending, setPending] = useState<Record<string, Record<string, unknown>>>({});

  if (detail.isLoading) return <div className="state-panel">Loading profile…</div>;
  const current = detail.data?.current_version;
  const draftVersions = (versions.data ?? []).filter((v) => v.status === "draft");

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <button
          type="button"
          className="tiny-btn"
          disabled={adopt.isPending}
          onClick={() => adopt.mutate(locationId)}
        >
          Adopt: link scenes with this location name
        </button>
        {adopt.isSuccess && (
          <p className="meta">Linked {adopt.data.matched_scene_ids.length} scene(s).</p>
        )}
      </div>

      <h4>Current approved version</h4>
      {current ? (
        <div className="tool-list-item">
          <p className="meta">v{current.version_number}</p>
          {Object.entries(current.profile).map(([field, envelope]) => {
            const e = envelope as Record<string, unknown>;
            return (
              <p key={field}>
                {field}: {String(e.value)} <span className="meta">({String(e.status)}, source: {String(e.source)})</span>
              </p>
            );
          })}
        </div>
      ) : (
        <div className="state-panel">No approved version yet.</div>
      )}

      {draftVersions.length > 0 && (
        <div style={{ marginTop: 14 }}>
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

      <div style={{ marginTop: 14 }}>
        <h4>Propose an edit</h4>
        <CharacteristicEditor onAdd={(field, envelope) => setPending((p) => ({ ...p, [field]: envelope }))} />
        {Object.keys(pending).length > 0 && <p className="meta">Pending in this edit: {Object.keys(pending).join(", ")}</p>}
        <button
          type="button"
          className="btn primary"
          disabled={Object.keys(pending).length === 0 || propose.isPending}
          onClick={() => propose.mutate({ profile_patch: pending }, { onSuccess: () => setPending({}) })}
        >
          {propose.isPending ? "Submitting…" : "Submit edit for approval"}
        </button>
        {propose.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(propose.error)}
          </p>
        )}
      </div>
    </div>
  );
}

function EnvironmentStatesTab({ projectId }: { projectId: string; locationId: string }) {
  const scenes = useScenes(projectId);
  const [sceneId, setSceneId] = useState("");
  const current = useEnvironmentState(projectId, sceneId);
  const create = useCreateEnvironmentState(projectId, sceneId);
  const [weather, setWeather] = useState("");
  const [timeOfDay, setTimeOfDay] = useState("");

  return (
    <div>
      <div className="tool-form" style={{ marginBottom: 12 }}>
        <label htmlFor="env-scene-select">Scene</label>
        <select id="env-scene-select" value={sceneId} onChange={(e) => setSceneId(e.target.value)}>
          <option value="">Select a scene…</option>
          {scenes.data?.map((s) => (
            <option key={s.id} value={s.id}>
              Scene {s.scene_number}: {s.heading}
            </option>
          ))}
        </select>
      </div>

      {sceneId && (
        <div>
          {current.data ? (
            <div className="tool-list-item">
              <p>Current: {JSON.stringify(current.data.changes)}</p>
            </div>
          ) : (
            <div className="state-panel">No environment state set for this scene yet.</div>
          )}
          <div className="tool-form" style={{ marginTop: 12 }}>
            <label>Weather</label>
            <input value={weather} onChange={(e) => setWeather(e.target.value)} aria-label="Weather" />
            <label>Time of day</label>
            <input value={timeOfDay} onChange={(e) => setTimeOfDay(e.target.value)} aria-label="Time of day" />
            <button
              type="button"
              className="btn small"
              disabled={create.isPending}
              onClick={() => create.mutate({ scene_id: sceneId, changes: { weather, time_of_day: timeOfDay } })}
            >
              Set environment state
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
