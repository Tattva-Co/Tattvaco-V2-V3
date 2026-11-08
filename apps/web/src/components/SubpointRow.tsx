import { useState } from "react";
import type { JourneySubpoint } from "../api/client";
import { StatusChip } from "./StatusChip";

const TERMINAL_STATUSES = new Set(["completed", "not_applicable"]);

export function SubpointRow({
  subpoint,
  index,
  canAct,
  naPolicy,
  isSystemDerived,
  onAct,
  pending,
}: {
  subpoint: JourneySubpoint;
  index: number;
  canAct: boolean;
  naPolicy: "never" | "reason_required";
  /** True for the `validate` subpoint of a group whose completion the server derives
   * automatically (packages/services/journey.py _evaluate_system_check; surfaced via
   * JourneyGroupResponse.system_managed): it cannot be marked complete by hand, so the
   * "Mark complete" action is hidden rather than shown-then-rejected. */
  isSystemDerived: boolean;
  onAct: (action: "draft" | "complete" | "request_review" | "not_applicable", reason?: string) => void;
  pending: boolean;
}) {
  const [showNaPrompt, setShowNaPrompt] = useState(false);
  const [naReason, setNaReason] = useState("");
  const isTerminal = TERMINAL_STATUSES.has(subpoint.status);
  const disabled = pending || !canAct;

  function submitNotApplicable() {
    onAct("not_applicable", naReason.trim() || undefined);
    setShowNaPrompt(false);
    setNaReason("");
  }

  return (
    <div className="subpoint">
      <div className="sub-num">{index}</div>
      <div>
        <div className="sub-title">{subpoint.title}</div>
        <div className="sub-desc">{subpoint.description}</div>
        {subpoint.not_applicable_reason && (
          <div className="sub-completion">Not applicable: {subpoint.not_applicable_reason}</div>
        )}
        {showNaPrompt && (
          <div style={{ marginTop: 8, display: "flex", gap: 6 }}>
            <input
              aria-label="Reason this item is not applicable"
              placeholder="Why doesn't this apply?"
              value={naReason}
              onChange={(e) => setNaReason(e.target.value)}
              style={{ flex: 1, padding: 6, borderRadius: 6, border: "1px solid var(--line)", fontSize: 11 }}
            />
            <button type="button" className="tiny-btn primary" onClick={submitNotApplicable} disabled={!naReason.trim()}>
              Confirm
            </button>
            <button type="button" className="tiny-btn" onClick={() => setShowNaPrompt(false)}>
              Cancel
            </button>
          </div>
        )}
      </div>
      <div className="sub-actions">
        <StatusChip status={subpoint.status} />
        {!isTerminal && canAct && !isSystemDerived && (
          <>
            {subpoint.status === "not_started" && (
              <button type="button" className="tiny-btn" disabled={disabled} onClick={() => onAct("draft")}>
                Save draft
              </button>
            )}
            {subpoint.kind === "review_gate" ? (
              <button type="button" className="tiny-btn" disabled={disabled} onClick={() => onAct("request_review")}>
                Request review
              </button>
            ) : null}
            <button type="button" className="tiny-btn primary" disabled={disabled} onClick={() => onAct("complete")}>
              Mark complete
            </button>
            {naPolicy !== "never" && (
              <button type="button" className="tiny-btn" disabled={disabled} onClick={() => setShowNaPrompt(true)}>
                Not applicable
              </button>
            )}
          </>
        )}
        {isSystemDerived && !isTerminal && (
          <span style={{ fontSize: 9, color: "var(--muted)" }}>Completes automatically</span>
        )}
      </div>
    </div>
  );
}
