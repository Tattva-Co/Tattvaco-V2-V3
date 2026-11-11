import { useState } from "react";
import type { Approval, Candidates } from "../../api/client";
import { useCandidates, useDecideApproval } from "../../hooks/useCandidates";
import { describeError } from "../../lib/describeError";

const SCOPE_LABEL: Record<string, string> = {
  script_intelligence_candidates: "Screenplay extraction",
  historical_research_candidates: "Historical research",
  storyboard_candidates: "Storyboard panels",
  film_bible_rules: "Visual world rules",
};

function useCheckedIds(initialIds: string[]) {
  const [checked, setChecked] = useState<Set<string>>(new Set(initialIds));
  const toggle = (id: string) =>
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  return { checked, toggle };
}

function ApprovalCard({
  approval,
  candidates,
  onDecide,
  pending,
}: {
  approval: Approval;
  candidates: Candidates;
  onDecide: (decision: "approved" | "rejected", notes: string, selections: Record<string, string[]>) => void;
  pending: boolean;
}) {
  const [notes, setNotes] = useState("");
  const runId = approval.workflow_run_id;

  const scenes = candidates.scenes.filter((s) => s.workflow_run_id === runId && s.status === "proposed");
  const entities = candidates.entities.filter((e) => e.workflow_run_id === runId && e.status === "proposed");
  const claims = (candidates.research_claims ?? []).filter((c) => c.workflow_run_id === runId && c.status === "proposed");
  const questions = (candidates.research_questions ?? []).filter(
    (q) => q.workflow_run_id === runId && q.status === "proposed"
  );
  const panels = (candidates.storyboard_panels ?? []).filter((p) => p.workflow_run_id === runId && p.status === "proposed");
  const rules = (candidates.film_bible_rules ?? []).filter((r) => r.workflow_run_id === runId && r.status === "proposed");

  const sceneIds = useCheckedIds(scenes.map((s) => s.id));
  const entityIds = useCheckedIds(entities.map((e) => e.id));
  const claimIds = useCheckedIds(claims.map((c) => c.id));
  const questionIds = useCheckedIds(questions.map((q) => q.id));
  const panelIds = useCheckedIds(panels.map((p) => p.id));
  const ruleIds = useCheckedIds(rules.map((r) => r.id));

  function approve() {
    onDecide("approved", notes, {
      approved_scene_ids: [...sceneIds.checked],
      approved_entity_ids: [...entityIds.checked],
      approved_claim_ids: [...claimIds.checked],
      approved_question_ids: [...questionIds.checked],
      approved_panel_ids: [...panelIds.checked],
      approved_rule_ids: [...ruleIds.checked],
    });
  }

  function reject() {
    onDecide("rejected", notes, {});
  }

  return (
    <div className="tool-list-item">
      <h4>{SCOPE_LABEL[approval.scope] ?? approval.scope}</h4>
      <p className="meta" style={{ marginBottom: 10 }}>
        {approval.workflow_run_id ? (
          <>
            Workflow run <code>{approval.workflow_run_id.slice(0, 8)}</code>
          </>
        ) : (
          <>
            {approval.target_type ?? "Target"} <code>{(approval.target_id ?? "unknown").slice(0, 8)}</code>
          </>
        )}
      </p>

      {scenes.length > 0 && (
        <fieldset style={{ border: 0, padding: 0, margin: "0 0 10px" }}>
          <legend style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)" }}>Proposed scenes</legend>
          {scenes.map((s) => (
            <label key={s.id} style={{ display: "block", fontSize: 11, padding: "4px 0" }}>
              <input type="checkbox" checked={sceneIds.checked.has(s.id)} onChange={() => sceneIds.toggle(s.id)} /> Scene{" "}
              {s.scene_number}: {s.heading} ({s.setting} / {s.time_of_day})
            </label>
          ))}
        </fieldset>
      )}

      {entities.length > 0 && (
        <fieldset style={{ border: 0, padding: 0, margin: "0 0 10px" }}>
          <legend style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)" }}>Proposed entities</legend>
          {entities.map((e) => (
            <label key={e.id} style={{ display: "block", fontSize: 11, padding: "4px 0" }}>
              <input type="checkbox" checked={entityIds.checked.has(e.id)} onChange={() => entityIds.toggle(e.id)} /> [
              {e.category}] {e.name} ({Math.round(e.confidence * 100)}%)
            </label>
          ))}
        </fieldset>
      )}

      {claims.length > 0 && (
        <fieldset style={{ border: 0, padding: 0, margin: "0 0 10px" }}>
          <legend style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)" }}>Proposed claims</legend>
          {claims.map((c) => (
            <label key={c.id} style={{ display: "block", fontSize: 11, padding: "4px 0" }}>
              <input type="checkbox" checked={claimIds.checked.has(c.id)} onChange={() => claimIds.toggle(c.id)} /> [
              {c.claim_class}] {c.statement}
            </label>
          ))}
        </fieldset>
      )}

      {questions.length > 0 && (
        <fieldset style={{ border: 0, padding: 0, margin: "0 0 10px" }}>
          <legend style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)" }}>Proposed questions</legend>
          {questions.map((q) => (
            <label key={q.id} style={{ display: "block", fontSize: 11, padding: "4px 0" }}>
              <input
                type="checkbox"
                checked={questionIds.checked.has(q.id)}
                onChange={() => questionIds.toggle(q.id)}
              />{" "}
              [{q.category}] {q.text}
            </label>
          ))}
        </fieldset>
      )}

      {panels.length > 0 && (
        <fieldset style={{ border: 0, padding: 0, margin: "0 0 10px" }}>
          <legend style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)" }}>Proposed panels</legend>
          {panels.map((p) => (
            <label key={p.id} style={{ display: "block", fontSize: 11, padding: "4px 0" }}>
              <input type="checkbox" checked={panelIds.checked.has(p.id)} onChange={() => panelIds.toggle(p.id)} /> Panel #
              {p.panel_number} [{p.shot_type}] -- {p.description}
            </label>
          ))}
        </fieldset>
      )}

      {rules.length > 0 && (
        <fieldset style={{ border: 0, padding: 0, margin: "0 0 10px" }}>
          <legend style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)" }}>Proposed rules</legend>
          {rules.map((r) => (
            <label key={r.id} style={{ display: "block", fontSize: 11, padding: "4px 0" }}>
              <input type="checkbox" checked={ruleIds.checked.has(r.id)} onChange={() => ruleIds.toggle(r.id)} /> [
              {r.category}] {r.title} ({r.strictness})
              {r.conflict_warning && (
                <span style={{ color: "var(--red)" }}> -- conflict: {r.conflict_warning}</span>
              )}
            </label>
          ))}
        </fieldset>
      )}

      <input
        aria-label="Reviewer notes"
        placeholder="Reviewer notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        style={{ width: "100%", padding: 7, borderRadius: 6, border: "1px solid var(--line)", fontSize: 11, marginBottom: 8 }}
      />
      <div style={{ display: "flex", gap: 6 }}>
        <button type="button" className="tiny-btn primary" disabled={pending} onClick={approve}>
          Approve selected
        </button>
        <button type="button" className="tiny-btn" disabled={pending} onClick={reject}>
          Reject all
        </button>
      </div>
    </div>
  );
}

/** Maps to JRN-02.3 and every other section's review gate: the single place AI-extracted
 * candidates (from any of the 4 graphs) are approved into canonical project state.
 * Approval is a project-wide capability (approval.creative), so this tool is cross-stage,
 * not owned by one journey section. */
export function ReviewTool({ projectId }: { projectId: string }) {
  const candidates = useCandidates(projectId);
  const decide = useDecideApproval(projectId);

  if (candidates.isLoading) return <div className="state-panel">Loading pending approvals…</div>;
  if (candidates.isError) {
    return (
      <div className="state-panel error" role="alert">
        {describeError(candidates.error)}
      </div>
    );
  }

  const pending = (candidates.data?.approvals ?? []).filter((a) => a.status === "pending");
  if (pending.length === 0) {
    return <div className="state-panel">No pending approvals. All candidates have been reviewed.</div>;
  }

  return (
    <div>
      {decide.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11, marginBottom: 10 }}>
          {describeError(decide.error)}
        </p>
      )}
      {pending.map((approval) => (
        <ApprovalCard
          key={approval.id}
          approval={approval}
          candidates={candidates.data!}
          pending={decide.isPending}
          onDecide={(decision, notes, selections) =>
            decide.mutate({
              approvalId: approval.id,
              body: { decision, notes: notes || null, ...selections },
            })
          }
        />
      ))}
    </div>
  );
}
