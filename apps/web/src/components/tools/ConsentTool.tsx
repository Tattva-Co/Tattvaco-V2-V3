import { useState } from "react";
import {
  useCreateConsent,
  useCreatePerformer,
  useCreateVoiceProfile,
  useDecideConsent,
  usePerformerConsents,
  usePerformers,
  useRevokeConsent,
  useVoiceProfiles,
} from "../../hooks/useConsent";
import { describeError } from "../../lib/describeError";

const TABS = ["Performers & Consent", "Voice Profiles"] as const;
type Tab = (typeof TABS)[number];

/** S-DH-01 (JRN-04.7): performer registry, purpose-specific consent and the voice-clone
 * gate. Performer/consent creation returns 403 `policy_pending` until DEC-007/DEC-012
 * are approved -- that is the real, current, correct behaviour, not a bug. */
export function ConsentTool({ projectId }: { projectId: string }) {
  const [tab, setTab] = useState<Tab>("Performers & Consent");
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
      {tab === "Performers & Consent" && <PerformersTab projectId={projectId} />}
      {tab === "Voice Profiles" && <VoiceProfilesTab projectId={projectId} />}
    </div>
  );
}

function PerformersTab({ projectId }: { projectId: string }) {
  const performers = usePerformers(projectId);
  const createPerformer = useCreatePerformer(projectId);
  const [displayName, setDisplayName] = useState("");
  const [selectedId, setSelectedId] = useState("");

  return (
    <div>
      <p className="sub-desc" style={{ marginBottom: 14 }}>
        A real person with legal rights over their likeness, body data and voice.
        Creating one, and recording consent, requires Legal to have approved the
        retention policy and consent template first -- expect 403 `policy_pending`
        until then.
      </p>
      <div className="tool-form" style={{ marginBottom: 16 }}>
        <label>Display name</label>
        <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} aria-label="Display name" />
        <button
          type="button"
          className="btn small"
          disabled={!displayName.trim() || createPerformer.isPending}
          onClick={() => createPerformer.mutate({ display_name: displayName.trim() }, { onSuccess: () => setDisplayName("") })}
        >
          Register performer
        </button>
        {createPerformer.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(createPerformer.error)}
          </p>
        )}
      </div>

      {performers.isLoading && <div className="state-panel">Loading performers…</div>}
      {performers.data?.length === 0 && <div className="state-panel">No performers registered yet.</div>}
      {performers.data && performers.data.length > 0 && (
        <div className="tool-form" style={{ marginBottom: 14 }}>
          <label>Performer</label>
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} aria-label="Performer">
            <option value="">Select a performer…</option>
            {performers.data.map((p) => (
              <option key={p.id} value={p.id}>
                {p.display_name}
              </option>
            ))}
          </select>
        </div>
      )}
      {selectedId && <ConsentPanel projectId={projectId} performerId={selectedId} />}
    </div>
  );
}

const CONSENT_PURPOSES = ["reference_storage", "digital_double", "voice_clone"];

function ConsentPanel({ projectId, performerId }: { projectId: string; performerId: string }) {
  const consents = usePerformerConsents(projectId, performerId);
  const create = useCreateConsent(projectId, performerId);
  const decide = useDecideConsent(projectId, performerId);
  const revoke = useRevokeConsent(projectId, performerId);
  const [purpose, setPurpose] = useState(CONSENT_PURPOSES[0]);

  return (
    <div>
      <h4>Consents</h4>
      {consents.data?.length === 0 && <div className="state-panel">No consent records yet.</div>}
      {consents.data?.map((c) => (
        <div key={c.id} className="tool-list-item">
          <p>
            {c.purpose} <span className="meta">({c.status}, v{c.version})</span>
          </p>
          {c.status === "draft" && (
            <button type="button" className="tiny-btn" onClick={() => decide.mutate({ consentId: c.id, body: { decision: "approved" } })}>
              Approve
            </button>
          )}
          {c.status === "active" && (
            <button
              type="button"
              className="tiny-btn"
              onClick={() => revoke.mutate({ performer_id: performerId, purpose: c.purpose, reason: "revoked from Studio Tools" })}
            >
              Revoke
            </button>
          )}
        </div>
      ))}
      <div className="tool-form" style={{ marginTop: 12 }}>
        <label>Purpose</label>
        <select value={purpose} onChange={(e) => setPurpose(e.target.value)} aria-label="Purpose">
          {CONSENT_PURPOSES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <button type="button" className="btn small" disabled={create.isPending} onClick={() => create.mutate({ purpose })}>
          Record consent (starts in draft)
        </button>
        {create.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(create.error)}
          </p>
        )}
      </div>
    </div>
  );
}

function VoiceProfilesTab({ projectId }: { projectId: string }) {
  const profiles = useVoiceProfiles(projectId);
  const create = useCreateVoiceProfile(projectId);
  const [kind, setKind] = useState("original_recording");
  const [performerId, setPerformerId] = useState("");

  return (
    <div>
      <p className="sub-desc" style={{ marginBottom: 14 }}>
        Permission to use recorded audio is not permission to clone it -- `voice_clone`
        consent is checked independently of `reference_storage`.
      </p>
      {profiles.data?.length === 0 && <div className="state-panel">No voice profiles yet.</div>}
      {profiles.data?.map((p) => (
        <div key={p.id} className="tool-list-item">
          <p>{p.kind}</p>
          <p className="meta">performer: {p.performer_id ?? "none"}</p>
        </div>
      ))}
      <div className="tool-form" style={{ marginTop: 12 }}>
        <label>Kind</label>
        <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Kind">
          <option value="original_recording">Original recording</option>
          <option value="clone">Clone</option>
        </select>
        <label>Performer ID (optional)</label>
        <input value={performerId} onChange={(e) => setPerformerId(e.target.value)} aria-label="Performer ID (optional)" />
        <button
          type="button"
          className="btn small"
          disabled={create.isPending}
          onClick={() => create.mutate({ kind, performer_id: performerId.trim() || null })}
        >
          Create voice profile
        </button>
        {create.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(create.error)}
          </p>
        )}
      </div>
    </div>
  );
}
