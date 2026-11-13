import { useState } from "react";
import { useCharacters, useScenes } from "../../hooks/useFilmBible";
import {
  useContinuityFindings,
  useCostumeDetail,
  useCostumes,
  useCostumeStates,
  useCostumeVersions,
  useCreateCostume,
  useCreateCostumeAssignment,
  useCreateCostumeState,
  useCreateProp,
  useCreatePropState,
  useDecideCostumeVersion,
  usePropStates,
  useProposeCostumeVersion,
  useProps,
} from "../../hooks/useVisualWorld";
import { describeError } from "../../lib/describeError";

const TABS = ["Costumes", "Assignments", "Continuity Findings", "Props & Weapons"] as const;
type Tab = (typeof TABS)[number];

/** S-CST-01/S-CST-02 (JRN-05.4/05.5): Costume Bible, costume states, character x scene
 * assignment (with its continuity-finding seam), and the props/weapons register. */
export function CostumePropsTool({ projectId }: { projectId: string }) {
  const [tab, setTab] = useState<Tab>("Costumes");
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
      {tab === "Costumes" && <CostumesTab projectId={projectId} />}
      {tab === "Assignments" && <AssignmentsTab projectId={projectId} />}
      {tab === "Continuity Findings" && <FindingsTab projectId={projectId} />}
      {tab === "Props & Weapons" && <PropsTab projectId={projectId} />}
    </div>
  );
}

function CostumesTab({ projectId }: { projectId: string }) {
  const costumes = useCostumes(projectId);
  const characters = useCharacters(projectId);
  const createCostume = useCreateCostume(projectId);
  const [name, setName] = useState("");
  const [characterId, setCharacterId] = useState("");
  const [selectedId, setSelectedId] = useState("");

  return (
    <div>
      <div className="tool-form" style={{ marginBottom: 16 }}>
        <label>Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} aria-label="Costume name" />
        <label>Default owner (optional)</label>
        <select value={characterId} onChange={(e) => setCharacterId(e.target.value)} aria-label="Default owner">
          <option value="">None</option>
          {characters.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.canonical_name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn small"
          disabled={!name.trim() || createCostume.isPending}
          onClick={() =>
            createCostume.mutate({ name: name.trim(), character_id: characterId || null }, { onSuccess: () => setName("") })
          }
        >
          Create costume
        </button>
      </div>

      {costumes.data?.length === 0 && <div className="state-panel">No costumes yet.</div>}
      {costumes.data && costumes.data.length > 0 && (
        <div className="tool-form" style={{ marginBottom: 14 }}>
          <label>Costume</label>
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} aria-label="Costume">
            <option value="">Select a costume…</option>
            {costumes.data.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}
      {selectedId && <CostumeDetail projectId={projectId} costumeId={selectedId} />}
    </div>
  );
}

const PROVENANCE_SOURCES = ["screenplay", "research_claim", "director", "ai_candidate", "performer_measurement", "scan"];

function CostumeDetail({ projectId, costumeId }: { projectId: string; costumeId: string }) {
  const detail = useCostumeDetail(projectId, costumeId);
  const versions = useCostumeVersions(projectId, costumeId);
  const states = useCostumeStates(projectId, costumeId);
  const propose = useProposeCostumeVersion(projectId, costumeId);
  const decide = useDecideCostumeVersion(projectId, costumeId);
  const createState = useCreateCostumeState(projectId, costumeId);
  const [field, setField] = useState("");
  const [value, setValue] = useState("");
  const [source, setSource] = useState(PROVENANCE_SOURCES[2]);
  const [claimLinks, setClaimLinks] = useState("");
  const [pending, setPending] = useState<Record<string, Record<string, unknown>>>({});
  const [stateLabel, setStateLabel] = useState("");

  if (detail.isLoading) return <div className="state-panel">Loading…</div>;
  const current = detail.data?.current_version;
  const draftVersions = (versions.data ?? []).filter((v) => v.status === "draft");

  return (
    <div>
      <h4>Current approved version</h4>
      {current ? (
        <div className="tool-list-item">
          <p className="meta">v{current.version_number} · claims: {current.claim_links.join(", ") || "none"}</p>
          {Object.entries(current.profile).map(([f, envelope]) => {
            const e = envelope as Record<string, unknown>;
            return (
              <p key={f}>
                {f}: {String(e.value)} <span className="meta">(source: {String(e.source)})</span>
              </p>
            );
          })}
        </div>
      ) : (
        <div className="state-panel">No approved version yet.</div>
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

      <div style={{ marginTop: 14 }}>
        <h4>Propose an edit</h4>
        <div className="tool-form" style={{ marginBottom: 8 }}>
          <label>Field (garments, materials, colours)</label>
          <input value={field} onChange={(e) => setField(e.target.value)} aria-label="Field name" />
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
          <button
            type="button"
            className="tiny-btn"
            disabled={!field.trim() || !value.trim()}
            onClick={() => {
              setPending((p) => ({ ...p, [field.trim()]: { value, source, status: "approved", approved_by: null } }));
              setField("");
              setValue("");
            }}
          >
            Add characteristic
          </button>
        </div>
        <label>Linked research claim IDs (comma-separated)</label>
        <input value={claimLinks} onChange={(e) => setClaimLinks(e.target.value)} aria-label="Linked research claim IDs" />
        {Object.keys(pending).length > 0 && <p className="meta">Pending: {Object.keys(pending).join(", ")}</p>}
        <button
          type="button"
          className="btn primary"
          disabled={propose.isPending}
          onClick={() =>
            propose.mutate(
              {
                profile_patch: pending,
                claim_links: claimLinks.trim() ? claimLinks.split(",").map((s) => s.trim()) : null,
              },
              { onSuccess: () => setPending({}) }
            )
          }
        >
          Submit edit for approval
        </button>
        {propose.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(propose.error)}
          </p>
        )}
      </div>

      <div style={{ marginTop: 14 }}>
        <h4>States</h4>
        {states.data?.map((s) => (
          <div key={s.id} className="tool-list-item">
            <p>
              {s.state_label} <span className="meta">v{s.version}</span>
            </p>
          </div>
        ))}
        <div className="tool-form" style={{ marginTop: 8 }}>
          <label>State label (e.g. clean, battle-damaged)</label>
          <input value={stateLabel} onChange={(e) => setStateLabel(e.target.value)} aria-label="State label" />
          <button
            type="button"
            className="btn small"
            disabled={!stateLabel.trim() || createState.isPending}
            onClick={() => createState.mutate({ state_label: stateLabel.trim() }, { onSuccess: () => setStateLabel("") })}
          >
            Add/update state
          </button>
        </div>
      </div>
    </div>
  );
}

function AssignmentsTab({ projectId }: { projectId: string }) {
  const characters = useCharacters(projectId);
  const scenes = useScenes(projectId);
  const costumes = useCostumes(projectId);
  const assign = useCreateCostumeAssignment(projectId);
  const [characterId, setCharacterId] = useState("");
  const [sceneId, setSceneId] = useState("");
  const [costumeId, setCostumeId] = useState("");

  return (
    <div>
      <p className="sub-desc" style={{ marginBottom: 14 }}>
        Assigning a second costume to the same character, scene and state is not
        silently resolved -- both assignments persist, and a continuity finding is
        raised (see the Continuity Findings tab).
      </p>
      <div className="tool-form">
        <label>Character</label>
        <select value={characterId} onChange={(e) => setCharacterId(e.target.value)} aria-label="Character">
          <option value="">Select…</option>
          {characters.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.canonical_name}
            </option>
          ))}
        </select>
        <label>Scene</label>
        <select value={sceneId} onChange={(e) => setSceneId(e.target.value)} aria-label="Scene">
          <option value="">Select…</option>
          {scenes.data?.map((s) => (
            <option key={s.id} value={s.id}>
              Scene {s.scene_number}: {s.heading}
            </option>
          ))}
        </select>
        <label>Costume</label>
        <select value={costumeId} onChange={(e) => setCostumeId(e.target.value)} aria-label="Costume">
          <option value="">Select…</option>
          {costumes.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn small"
          disabled={!characterId || !sceneId || !costumeId || assign.isPending}
          onClick={() => assign.mutate({ character_id: characterId, scene_id: sceneId, costume_id: costumeId })}
        >
          Assign costume
        </button>
        {assign.isSuccess && <p style={{ color: "var(--green)", fontSize: 11 }}>Assigned.</p>}
        {assign.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(assign.error)}
          </p>
        )}
      </div>
    </div>
  );
}

function FindingsTab({ projectId }: { projectId: string }) {
  const findings = useContinuityFindings(projectId);
  return (
    <div>
      {findings.data?.length === 0 && <div className="state-panel">No continuity findings.</div>}
      {findings.data?.map((f) => (
        <div key={f.id} className="tool-list-item">
          <h4>{f.finding_type}</h4>
          <p className="meta">{f.status}</p>
          <p>{JSON.stringify(f.details)}</p>
        </div>
      ))}
    </div>
  );
}

function PropsTab({ projectId }: { projectId: string }) {
  const props = useProps(projectId);
  const characters = useCharacters(projectId);
  const scenes = useScenes(projectId);
  const createProp = useCreateProp(projectId);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("prop");
  const [ownerId, setOwnerId] = useState("");
  const [selectedPropId, setSelectedPropId] = useState("");

  return (
    <div>
      <div className="tool-form" style={{ marginBottom: 16 }}>
        <label>Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} aria-label="Prop name" />
        <label>Kind</label>
        <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Kind">
          <option value="prop">Prop</option>
          <option value="weapon">Weapon</option>
        </select>
        <label>Owner (optional)</label>
        <select value={ownerId} onChange={(e) => setOwnerId(e.target.value)} aria-label="Owner">
          <option value="">None</option>
          {characters.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.canonical_name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn small"
          disabled={!name.trim() || createProp.isPending}
          onClick={() =>
            createProp.mutate(
              { name: name.trim(), kind, owner_character_id: ownerId || null },
              { onSuccess: () => setName("") }
            )
          }
        >
          Register prop
        </button>
        {createProp.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(createProp.error)}
          </p>
        )}
      </div>

      {props.data?.length === 0 && <div className="state-panel">No props registered yet.</div>}
      {props.data && props.data.length > 0 && (
        <div className="tool-form" style={{ marginBottom: 14 }}>
          <label>Prop</label>
          <select value={selectedPropId} onChange={(e) => setSelectedPropId(e.target.value)} aria-label="Select prop">
            <option value="">Select a prop…</option>
            {props.data.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.kind})
              </option>
            ))}
          </select>
        </div>
      )}
      {selectedPropId && <PropStatesPanel projectId={projectId} propId={selectedPropId} scenes={scenes.data ?? []} characters={characters.data ?? []} />}
    </div>
  );
}

function PropStatesPanel({
  projectId,
  propId,
  scenes,
  characters,
}: {
  projectId: string;
  propId: string;
  scenes: { id: string; scene_number: number; heading: string }[];
  characters: { id: string; canonical_name: string }[];
}) {
  const states = usePropStates(projectId, propId);
  const createState = useCreatePropState(projectId, propId);
  const [sceneId, setSceneId] = useState("");
  const [holderId, setHolderId] = useState("");

  return (
    <div>
      {states.data?.map((s) => (
        <div key={s.id} className="tool-list-item">
          <p className="meta">
            scene {scenes.find((sc) => sc.id === s.scene_id)?.scene_number ?? s.scene_id} · holder:{" "}
            {characters.find((c) => c.id === s.holder_character_id)?.canonical_name ?? "none"}
          </p>
        </div>
      ))}
      <div className="tool-form" style={{ marginTop: 8 }}>
        <label>Scene</label>
        <select value={sceneId} onChange={(e) => setSceneId(e.target.value)} aria-label="Prop state scene">
          <option value="">Select…</option>
          {scenes.map((s) => (
            <option key={s.id} value={s.id}>
              Scene {s.scene_number}: {s.heading}
            </option>
          ))}
        </select>
        <label>Holder (optional)</label>
        <select value={holderId} onChange={(e) => setHolderId(e.target.value)} aria-label="Prop holder">
          <option value="">Not held</option>
          {characters.map((c) => (
            <option key={c.id} value={c.id}>
              {c.canonical_name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn small"
          disabled={!sceneId || createState.isPending}
          onClick={() => createState.mutate({ scene_id: sceneId, holder_character_id: holderId || null })}
        >
          Record state
        </button>
      </div>
    </div>
  );
}
