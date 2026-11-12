import { useState } from "react";
import type { ScreenplayVersion } from "../../api/client";
import {
  useConfirmLegacyLock,
  useDecideScreenplayRevision,
  useDecideScreenplaySuggestion,
  useGenerateScreenplaySuggestions,
  useImpactAnalyses,
  useImpactPreview,
  useReviseScreenplay,
  useScreenplayDiff,
  useScreenplaySuggestions,
  useScreenplayVersion,
  useScreenplayVersions,
  useSubmitScreenplayRevision,
  useUpdateScreenplayVersion,
} from "../../hooks/useScreenplay";
import { describeError } from "../../lib/describeError";

const TABS = ["Versions", "Suggestions", "Impact Analysis"] as const;
type Tab = (typeof TABS)[number];

function RevisionEditor({
  projectId,
  versionId,
  onDone,
}: {
  projectId: string;
  versionId: string;
  onDone: () => void;
}) {
  const version = useScreenplayVersion(projectId, versionId);
  const update = useUpdateScreenplayVersion(projectId);
  const submit = useSubmitScreenplayRevision(projectId);
  const [content, setContent] = useState<string | null>(null);
  const [justification, setJustification] = useState("");
  const [showDiff, setShowDiff] = useState(false);
  const diffAgainst = version.data?.derived_from_version_id ?? undefined;
  const diff = useScreenplayDiff(projectId, versionId, showDiff ? diffAgainst : undefined);

  if (version.isLoading) return <div className="state-panel">Loading revision…</div>;
  const v = version.data;
  if (!v) return null;

  const text = content ?? v.content_text;
  const dirty = text !== v.content_text;

  return (
    <div>
      <button type="button" className="tiny-btn" onClick={onDone} style={{ marginBottom: 10 }}>
        ← Back to versions
      </button>
      <h4>
        Editing v{v.version_number} ({v.status})
      </h4>
      <textarea
        aria-label="Screenplay text"
        value={text}
        onChange={(e) => setContent(e.target.value)}
        rows={14}
        style={{ width: "100%", fontFamily: "monospace", fontSize: 12, marginTop: 8 }}
      />
      <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
        <button
          type="button"
          className="btn small"
          disabled={!dirty || update.isPending}
          onClick={() => update.mutate({ versionId, body: { content_text: text } }, { onSuccess: () => setContent(null) })}
        >
          {update.isPending ? "Saving…" : "Save draft"}
        </button>
        {v.derived_from_version_id && (
          <button type="button" className="tiny-btn" onClick={() => setShowDiff((s) => !s)}>
            {showDiff ? "Hide diff" : "View diff vs. base"}
          </button>
        )}
      </div>
      {update.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
          {describeError(update.error)}
        </p>
      )}

      {showDiff && diff.data && (
        <pre
          style={{
            fontSize: 11,
            background: "var(--panel)",
            padding: 10,
            marginTop: 8,
            maxHeight: 200,
            overflow: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
          {diff.data.unified_diff || "No textual difference."}
        </pre>
      )}

      <div className="tool-form" style={{ marginTop: 14 }}>
        <label htmlFor="justification">Justification (required to submit for review)</label>
        <textarea
          id="justification"
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          rows={3}
        />
        <button
          type="button"
          className="btn primary small"
          disabled={!justification.trim() || submit.isPending || dirty}
          onClick={() =>
            submit.mutate({ versionId, justification: justification.trim() }, { onSuccess: onDone })
          }
        >
          {submit.isPending ? "Submitting…" : "Submit for management review"}
        </button>
        {dirty && <p className="meta">Save your changes before submitting.</p>}
        {submit.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(submit.error)}
          </p>
        )}
      </div>
    </div>
  );
}

function DecisionPanel({ projectId, version }: { projectId: string; version: ScreenplayVersion }) {
  const decide = useDecideScreenplayRevision(projectId);
  const impactPreview = useImpactPreview(projectId, version.id);
  const [notes, setNotes] = useState("");

  return (
    <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--line)" }}>
      {impactPreview.data && impactPreview.data.affected_items.length > 0 && (
        <p className="meta" style={{ color: "var(--amber, #b58900)" }}>
          Approving this will flag {impactPreview.data.affected_items.length} existing canonical item(s) for review.
        </p>
      )}
      <input
        aria-label="Decision notes"
        placeholder="Notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        style={{ width: "100%", marginBottom: 6 }}
      />
      <div style={{ display: "flex", gap: 6 }}>
        <button
          type="button"
          className="tiny-btn primary"
          disabled={decide.isPending}
          onClick={() => decide.mutate({ versionId: version.id, body: { decision: "approved", notes: notes || null } })}
        >
          Approve & lock
        </button>
        <button
          type="button"
          className="tiny-btn"
          disabled={decide.isPending}
          onClick={() =>
            decide.mutate({ versionId: version.id, body: { decision: "changes_requested", notes: notes || null } })
          }
        >
          Request changes
        </button>
        <button
          type="button"
          className="tiny-btn"
          disabled={decide.isPending}
          onClick={() => decide.mutate({ versionId: version.id, body: { decision: "rejected", notes: notes || null } })}
        >
          Reject
        </button>
      </div>
      {decide.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
          {describeError(decide.error)}
        </p>
      )}
    </div>
  );
}

function VersionsTab({ projectId }: { projectId: string }) {
  const versions = useScreenplayVersions(projectId);
  const revise = useReviseScreenplay(projectId);
  const confirmLock = useConfirmLegacyLock(projectId);
  const [editingVersionId, setEditingVersionId] = useState<string | null>(null);

  if (editingVersionId) {
    return (
      <RevisionEditor projectId={projectId} versionId={editingVersionId} onDone={() => setEditingVersionId(null)} />
    );
  }

  if (versions.isLoading) return <div className="state-panel">Loading screenplay versions…</div>;
  if (versions.data?.length === 0) {
    return <div className="state-panel">No screenplay versions yet -- import one in the Script Intelligence tool.</div>;
  }

  return (
    <div>
      {versions.data?.map((v) => (
        <div key={v.id} className="tool-list-item">
          <h4>
            v{v.version_number}{" "}
            {v.is_production_canonical && <span className="tag amber">canonical</span>}
          </h4>
          <p className="meta">
            {v.status}
            {v.derived_from_version_id ? " · revision" : " · imported"}
          </p>
          <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
            {v.status === "draft" && (
              <button type="button" className="tiny-btn" onClick={() => setEditingVersionId(v.id)}>
                Edit & submit
              </button>
            )}
            {v.status === "approved_locked" && (
              <button
                type="button"
                className="tiny-btn"
                disabled={revise.isPending}
                onClick={() => revise.mutate(v.id, { onSuccess: (newV) => setEditingVersionId(newV.id) })}
              >
                Create revision
              </button>
            )}
            {v.status === "draft" && !v.derived_from_version_id && !v.is_production_canonical && (
              <button
                type="button"
                className="tiny-btn"
                disabled={confirmLock.isPending}
                onClick={() => confirmLock.mutate(v.id)}
              >
                Confirm as production lock
              </button>
            )}
          </div>
          {v.status === "in_review" && <DecisionPanel projectId={projectId} version={v} />}
          {confirmLock.isError && (
            <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
              {describeError(confirmLock.error)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function SuggestionsTab({ projectId }: { projectId: string }) {
  const versions = useScreenplayVersions(projectId);
  const [versionId, setVersionId] = useState("");
  const suggestions = useScreenplaySuggestions(projectId, versionId || undefined);
  const generate = useGenerateScreenplaySuggestions(projectId, versionId);
  const decide = useDecideScreenplaySuggestion(projectId, versionId);
  const [scopeNotes, setScopeNotes] = useState("");

  return (
    <div>
      <div className="tool-form" style={{ marginBottom: 16 }}>
        <label htmlFor="suggestion-version">Screenplay version</label>
        <select id="suggestion-version" value={versionId} onChange={(e) => setVersionId(e.target.value)}>
          <option value="">Select a version…</option>
          {versions.data?.map((v) => (
            <option key={v.id} value={v.id}>
              v{v.version_number} ({v.status})
            </option>
          ))}
        </select>
        <input
          placeholder="Scope notes (optional)"
          value={scopeNotes}
          onChange={(e) => setScopeNotes(e.target.value)}
        />
        <button
          type="button"
          className="btn small"
          disabled={!versionId || generate.isPending}
          onClick={() => generate.mutate({ scope_notes: scopeNotes || null })}
        >
          {generate.isPending ? "Generating…" : "Generate suggestions"}
        </button>
      </div>

      {!versionId && <div className="state-panel">Select a version to see its suggestions.</div>}
      {suggestions.data?.length === 0 && versionId && (
        <div className="state-panel">No suggestions yet for this version.</div>
      )}
      {suggestions.data?.map((s) => (
        <div key={s.id} className="tool-list-item">
          <h4>
            [{s.kind.replace(/_/g, " ")}] {s.anchor}
          </h4>
          <p>{s.suggestion_text}</p>
          {s.rationale && <p className="meta">{s.rationale}</p>}
          <p className="meta">
            {s.disposition} · {s.generator_mode}
          </p>
          {s.disposition === "pending" && (
            <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
              <button
                type="button"
                className="tiny-btn primary"
                onClick={() => decide.mutate({ suggestionId: s.id, body: { disposition: "accepted_for_revision" } })}
              >
                Accept for revision
              </button>
              <button
                type="button"
                className="tiny-btn"
                onClick={() => decide.mutate({ suggestionId: s.id, body: { disposition: "deferred" } })}
              >
                Defer
              </button>
              <button
                type="button"
                className="tiny-btn"
                onClick={() => decide.mutate({ suggestionId: s.id, body: { disposition: "rejected" } })}
              >
                Reject
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ImpactAnalysisTab({ projectId }: { projectId: string }) {
  const analyses = useImpactAnalyses(projectId);
  if (analyses.isLoading) return <div className="state-panel">Loading impact analyses…</div>;
  if (analyses.data?.length === 0) {
    return <div className="state-panel">No impact analyses yet -- these appear when a revision is locked.</div>;
  }
  return (
    <div>
      {analyses.data?.map((a) => (
        <div key={a.id} className="tool-list-item">
          <h4>{a.trigger_type.replace(/_/g, " ")}</h4>
          <p className="meta">{new Date(a.created_at).toLocaleString()}</p>
          <p className="meta">{a.affected_items.length} item(s) flagged for review</p>
          {a.affected_items.map((item, i) => (
            <p key={i} className="meta">
              {String(item.item_type)}: {String(item.reason)}
            </p>
          ))}
        </div>
      ))}
    </div>
  );
}

/** S-SCR-01..04: screenplay version history, director revisions, the Suggestions
 * Workspace, and impact analyses. Management's approve/reject/request-changes decision
 * lives inline on each in_review version (DecisionPanel), not a separate screen. */
export function ScreenplayGovernanceTool({ projectId }: { projectId: string }) {
  const [tab, setTab] = useState<Tab>("Versions");
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
      {tab === "Versions" && <VersionsTab projectId={projectId} />}
      {tab === "Suggestions" && <SuggestionsTab projectId={projectId} />}
      {tab === "Impact Analysis" && <ImpactAnalysisTab projectId={projectId} />}
    </div>
  );
}
