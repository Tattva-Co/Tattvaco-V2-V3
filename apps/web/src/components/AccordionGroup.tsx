import type { JourneyGroup, JourneyItemAction } from "../api/client";
import { StatusChip } from "./StatusChip";
import { SubpointRow } from "./SubpointRow";

export function AccordionGroup({
  group,
  index,
  isOpen,
  onToggle,
  onAct,
  pendingSubpointId,
}: {
  group: JourneyGroup;
  index: number;
  isOpen: boolean;
  onToggle: () => void;
  onAct: (jrnId: string, action: JourneyItemAction) => void;
  /** The jrn_subpoint_id currently in flight, so only that row shows a pending state
   * while the mutation is in the air (the journey-wide invalidate on success re-fetches
   * everything, so this is the only per-row signal available). */
  pendingSubpointId: string | null;
}) {
  const headingId = `acc-heading-${group.id}`;
  const panelId = `acc-panel-${group.id}`;

  return (
    <section className={`accordion${isOpen ? " open" : ""}`}>
      <button
        type="button"
        className="accordion-head"
        id={headingId}
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={onToggle}
      >
        <span className="acc-number">{String(index).padStart(2, "0")}</span>
        <div>
          <div className="acc-title">{group.title}</div>
          <div className="acc-sub">{group.purpose}</div>
        </div>
        <span className="acc-meta">
          <StatusChip status={group.status} />
        </span>
        <span className="chev" aria-hidden="true">
          {isOpen ? "−" : "+"}
        </span>
      </button>
      {isOpen && (
        <div className="accordion-body" id={panelId} role="region" aria-labelledby={headingId}>
          {!group.applies ? (
            <p className="sub-desc" style={{ padding: "10px 0" }}>
              Not applicable{group.applicability_reason ? `: ${group.applicability_reason}` : "."}
            </p>
          ) : (
            <>
              {group.requirements.length > 0 && (
                <p className="sub-desc" style={{ marginBottom: 10 }}>
                  Needs: {group.requirements.join(", ")}
                </p>
              )}
              {group.subpoints.map((subpoint, subIndex) => (
                <SubpointRow
                  key={subpoint.id}
                  subpoint={subpoint}
                  index={subIndex + 1}
                  canAct={group.can_act}
                  naPolicy={group.na_policy === "never" ? "never" : "reason_required"}
                  isSystemDerived={group.system_managed && subpoint.key === "validate"}
                  pending={pendingSubpointId === subpoint.id}
                  onAct={(action, reason) =>
                    onAct(subpoint.id, { action, not_applicable_reason: reason ?? null })
                  }
                />
              ))}
            </>
          )}
        </div>
      )}
    </section>
  );
}
