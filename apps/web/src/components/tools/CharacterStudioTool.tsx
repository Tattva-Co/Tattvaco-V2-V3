import { useState } from "react";
import { useCharacters, useScenes } from "../../hooks/useFilmBible";
import {
  useAddFacialReference,
  useCharacterDetail,
  useCharacterStates,
  useCharacterVersions,
  useCorrectMeasurement,
  useCreateCharacterState,
  useDecideCharacterVersion,
  useFacialReferences,
  useMeasurementHistory,
  useProposeCharacterVersion,
  useSaveMeasurement,
  useVerifyMeasurement,
} from "../../hooks/useCharacterStudio";
import { describeError } from "../../lib/describeError";

const TABS = ["Profile", "Facial References", "States", "Measurements"] as const;
type Tab = (typeof TABS)[number];

const PROVENANCE_SOURCES = ["screenplay", "research_claim", "director", "ai_candidate", "performer_measurement", "scan"];
const PROVENANCE_STATUSES = ["estimated", "verified", "approved", "disputed"];

/** S-CHR-01 (JRN-04.1/04.2/04.3/04.8): identity/physical profile versioning, facial
 * references and scene-anchored states, on top of the characters D3 already resolves. */
export function CharacterStudioTool({ projectId }: { projectId: string }) {
  const characters = useCharacters(projectId);
  const [characterId, setCharacterId] = useState("");

  if (characters.isLoading) return <div className="state-panel">Loading characters…</div>;
  if (!characters.data || characters.data.length === 0) {
    return <div className="state-panel">No canonical characters yet -- run Script Intelligence first.</div>;
  }

  return (
    <div>
      <div className="tool-form" style={{ marginBottom: 14 }}>
        <label htmlFor="character-select">Character</label>
        <select id="character-select" value={characterId} onChange={(e) => setCharacterId(e.target.value)}>
          <option value="">Select a character…</option>
          {characters.data.map((c) => (
            <option key={c.id} value={c.id}>
              {c.canonical_name}
            </option>
          ))}
        </select>
      </div>
      {characterId && <CharacterDetail projectId={projectId} characterId={characterId} />}
    </div>
  );
}

function CharacterDetail({ projectId, characterId }: { projectId: string; characterId: string }) {
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
      {tab === "Profile" && <ProfileTab projectId={projectId} characterId={characterId} />}
      {tab === "Facial References" && <FacialReferencesTab projectId={projectId} characterId={characterId} />}
      {tab === "States" && <StatesTab projectId={projectId} characterId={characterId} />}
      {tab === "Measurements" && <MeasurementsTab projectId={projectId} characterId={characterId} />}
    </div>
  );
}

function CharacteristicEditor({ onAdd }: { onAdd: (field: string, envelope: Record<string, unknown>) => void }) {
  const [field, setField] = useState("");
  const [value, setValue] = useState("");
  const [source, setSource] = useState(PROVENANCE_SOURCES[2]);
  const [status, setStatus] = useState(PROVENANCE_STATUSES[2]);
  const [confidence, setConfidence] = useState("1.0");

  return (
    <div className="tool-form" style={{ marginBottom: 12 }}>
      <label>Field name</label>
      <input
        value={field}
        onChange={(e) => setField(e.target.value)}
        placeholder="e.g. biography, height"
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
      <label>Confidence (0-1)</label>
      <input
        type="number"
        min={0}
        max={1}
        step={0.05}
        value={confidence}
        onChange={(e) => setConfidence(e.target.value)}
        aria-label="Confidence (0-1)"
      />
      <button
        type="button"
        className="btn small"
        disabled={!field.trim() || !value.trim()}
        onClick={() => {
          onAdd(field.trim(), { value, source, status, confidence: Number(confidence), approved_by: null });
          setField("");
          setValue("");
        }}
      >
        Add characteristic to this edit
      </button>
    </div>
  );
}

function ProfileTab({ projectId, characterId }: { projectId: string; characterId: string }) {
  const detail = useCharacterDetail(projectId, characterId);
  const versions = useCharacterVersions(projectId, characterId);
  const propose = useProposeCharacterVersion(projectId, characterId);
  const decide = useDecideCharacterVersion(projectId, characterId);
  const [facet, setFacet] = useState<"identity" | "physical">("identity");
  const [pending, setPending] = useState<Record<string, Record<string, unknown>>>({});

  if (detail.isLoading) return <div className="state-panel">Loading profile…</div>;
  const current = detail.data?.current_version;
  const draftVersions = (versions.data ?? []).filter((v) => v.status === "draft");

  return (
    <div>
      <h4>Current approved version</h4>
      {current ? (
        <div className="tool-list-item">
          <p className="meta">v{current.version_number} · approved {current.approved_at ? new Date(current.approved_at).toLocaleString() : ""}</p>
          <strong>Identity</strong>
          {Object.entries(current.identity_profile).map(([field, envelope]) => {
            const e = envelope as Record<string, unknown>;
            return (
              <p key={field}>
                {field}: {String(e.value)}{" "}
                <span className="meta">
                  ({String(e.status)}, source: {String(e.source)})
                </span>
              </p>
            );
          })}
          <strong>Physical</strong>
          {Object.entries(current.physical_profile).map(([field, envelope]) => {
            const e = envelope as Record<string, unknown>;
            return (
              <p key={field}>
                {field}: {String(e.value)}{" "}
                <span className="meta">
                  ({String(e.status)}, source: {String(e.source)})
                </span>
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
              <button
                type="button"
                className="btn small"
                onClick={() => decide.mutate({ versionId: v.id, body: { decision: "approved" } })}
              >
                Approve
              </button>{" "}
              <button
                type="button"
                className="tiny-btn"
                onClick={() => decide.mutate({ versionId: v.id, body: { decision: "rejected" } })}
              >
                Reject
              </button>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 14 }}>
        <h4>Propose an edit</h4>
        <div className="tool-form" style={{ marginBottom: 8 }}>
          <label>Facet</label>
          <select value={facet} onChange={(e) => setFacet(e.target.value as "identity" | "physical")} aria-label="Facet">
            <option value="identity">Identity</option>
            <option value="physical">Physical</option>
          </select>
        </div>
        <CharacteristicEditor onAdd={(field, envelope) => setPending((p) => ({ ...p, [field]: envelope }))} />
        {Object.keys(pending).length > 0 && (
          <p className="meta">Pending in this edit: {Object.keys(pending).join(", ")}</p>
        )}
        <button
          type="button"
          className="btn primary"
          disabled={Object.keys(pending).length === 0 || propose.isPending}
          onClick={() =>
            propose.mutate(
              { [facet === "identity" ? "identity_patch" : "physical_patch"]: pending },
              { onSuccess: () => setPending({}) }
            )
          }
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

function FacialReferencesTab({ projectId, characterId }: { projectId: string; characterId: string }) {
  const refs = useFacialReferences(projectId, characterId);
  const add = useAddFacialReference(projectId, characterId);
  const [assetId, setAssetId] = useState("");
  const [role, setRole] = useState("identity_front");

  return (
    <div>
      {refs.isLoading && <div className="state-panel">Loading…</div>}
      {refs.data?.length === 0 && <div className="state-panel">No facial references yet.</div>}
      {refs.data?.map((r) => (
        <div key={r.id} className="tool-list-item">
          <p>
            {r.role} · facial identity v{r.facial_identity_version}
          </p>
          <p className="meta">asset: {r.asset_id}</p>
        </div>
      ))}
      <div className="tool-form" style={{ marginTop: 12 }}>
        <label>Asset ID</label>
        <input
          value={assetId}
          onChange={(e) => setAssetId(e.target.value)}
          placeholder="Upload under Assets, then paste its ID"
          aria-label="Asset ID"
        />
        <label>Role</label>
        <select value={role} onChange={(e) => setRole(e.target.value)} aria-label="Role">
          <option value="identity_front">Front</option>
          <option value="identity_side">Side</option>
          <option value="identity_three_quarter">Three-quarter</option>
        </select>
        <button
          type="button"
          className="btn small"
          disabled={!assetId.trim() || add.isPending}
          onClick={() => add.mutate({ asset_id: assetId.trim(), role, facial_identity_version: 1 }, { onSuccess: () => setAssetId("") })}
        >
          Add reference
        </button>
        {add.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(add.error)}
          </p>
        )}
      </div>
    </div>
  );
}

function StatesTab({ projectId, characterId }: { projectId: string; characterId: string }) {
  const states = useCharacterStates(projectId, characterId);
  const scenes = useScenes(projectId);
  const create = useCreateCharacterState(projectId, characterId);
  const [label, setLabel] = useState("");
  const [fromSceneId, setFromSceneId] = useState("");

  const sceneHeading = (id: string) => scenes.data?.find((s) => s.id === id)?.heading ?? id;

  return (
    <div>
      {states.data?.length === 0 && <div className="state-panel">No character states defined yet.</div>}
      {states.data?.map((s) => (
        <div key={s.id} className="tool-list-item">
          <h4>{s.state_label}</h4>
          <p className="meta">from: {sceneHeading(s.applies_from_scene_id)}</p>
        </div>
      ))}
      <div className="tool-form" style={{ marginTop: 12 }}>
        <label>State label</label>
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g. wounded left arm"
          aria-label="State label"
        />
        <label>Applies from scene</label>
        <select value={fromSceneId} onChange={(e) => setFromSceneId(e.target.value)} aria-label="Applies from scene">
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
          disabled={!label.trim() || !fromSceneId || create.isPending}
          onClick={() =>
            create.mutate({ state_label: label.trim(), applies_from_scene_id: fromSceneId }, { onSuccess: () => setLabel("") })
          }
        >
          Add state
        </button>
      </div>
    </div>
  );
}

function MeasurementsTab({ projectId, characterId }: { projectId: string; characterId: string }) {
  const detail = useCharacterDetail(projectId, characterId);
  const subjectId = detail.data?.current_version?.id ?? "";
  const history = useMeasurementHistory(projectId, "character_version", subjectId);
  const save = useSaveMeasurement(projectId, "character_version", subjectId);
  const verify = useVerifyMeasurement(projectId, "character_version", subjectId);
  const correct = useCorrectMeasurement(projectId, "character_version", subjectId);
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("cm");
  const [method, setMethod] = useState("manual_entry");

  if (!subjectId) {
    return <div className="state-panel">Approve a character version first -- measurements attach to it.</div>;
  }

  return (
    <div>
      {history.data?.length === 0 && <div className="state-panel">No measurements recorded yet.</div>}
      {history.data?.map((m) => (
        <div key={m.id} className="tool-list-item">
          <p>
            {m.measurement_key}: {m.value} {m.unit} <span className="meta">({m.status})</span>
          </p>
          {m.status !== "verified" && m.status !== "superseded" && (
            <>
              <button type="button" className="tiny-btn" onClick={() => verify.mutate(m.id)}>
                Verify
              </button>{" "}
              <button
                type="button"
                className="tiny-btn"
                onClick={() => {
                  const next = window.prompt("Corrected value:", String(m.value));
                  if (next) correct.mutate({ measurementId: m.id, body: { value: Number(next) } });
                }}
              >
                Correct
              </button>
            </>
          )}
        </div>
      ))}
      <div className="tool-form" style={{ marginTop: 12 }}>
        <label>Measurement key</label>
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="e.g. height, chest_circumference"
          aria-label="Measurement key"
        />
        <label>Value</label>
        <input type="number" value={value} onChange={(e) => setValue(e.target.value)} aria-label="Measurement value" />
        <label>Unit</label>
        <input value={unit} onChange={(e) => setUnit(e.target.value)} aria-label="Unit" />
        <label>Capture method</label>
        <select value={method} onChange={(e) => setMethod(e.target.value)} aria-label="Capture method">
          <option value="manual_entry">Manual entry</option>
          <option value="ai_estimate">AI estimate</option>
          <option value="calibrated_scan">Calibrated scan</option>
        </select>
        <button
          type="button"
          className="btn small"
          disabled={!key.trim() || !value || save.isPending}
          onClick={() =>
            save.mutate(
              { subject_type: "character_version", subject_id: subjectId, measurement_key: key.trim(), value: Number(value), unit, capture_method: method },
              { onSuccess: () => { setKey(""); setValue(""); } }
            )
          }
        >
          Save measurement
        </button>
        {save.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(save.error)}
          </p>
        )}
      </div>
    </div>
  );
}
