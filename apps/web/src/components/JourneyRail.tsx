import { Link } from "react-router-dom";
import type { JourneySection, Project } from "../api/client";

/** A section is selectable once the previous one is ready_to_continue or completed
 * (JOURNEY_MANIFEST.md §7: "Section 01 is always open"). The server is the source of
 * truth for each section's OWN status; this is purely the navigation-unlock rule layered
 * on top, matching the wireframe's `isUnlocked` behaviour. */
function isUnlocked(sections: JourneySection[], index: number): boolean {
  if (index === 0) return true;
  const previous = sections[index - 1];
  return previous.status === "ready_to_continue" || previous.status === "completed";
}

export function JourneyRail({
  project,
  sections,
  activeSectionId,
  onSelectSection,
}: {
  project: Project;
  sections: JourneySection[];
  activeSectionId: string;
  onSelectSection: (sectionId: string) => void;
}) {
  const completedCount = sections.filter((s) => s.status === "completed" || s.status === "ready_to_continue").length;
  const progressPct = sections.length > 0 ? Math.round((completedCount / sections.length) * 100) : 0;

  return (
    <nav className="journey" aria-label="Production journey">
      <div className="journey-top">
        <Link to="/" className="back">
          ← Online Workspace
        </Link>
        <strong>{project.title}</strong>
        <small>{project.production_mode.replace(/_/g, " ")}</small>
      </div>
      <div className="journey-progress">
        <div className="line">
          <span style={{ width: `${progressPct}%` }} />
        </div>
        <small>
          {completedCount} of {sections.length} sections complete
        </small>
      </div>
      <div className="stage-list">
        {sections.map((section, index) => {
          const unlocked = isUnlocked(sections, index);
          const num = String(index + 1).padStart(2, "0");
          return (
            <button
              key={section.id}
              type="button"
              className={`stage-btn${section.id === activeSectionId ? " active" : ""}`}
              disabled={!unlocked}
              aria-current={section.id === activeSectionId ? "step" : undefined}
              title={unlocked ? undefined : "Complete the required work in the previous section first"}
              onClick={() => unlocked && onSelectSection(section.id)}
            >
              <span className="stage-num">{num}</span>
              <span className="stage-title">{section.title}</span>
              <span className="stage-status" aria-hidden="true">
                {section.status === "completed" || section.status === "ready_to_continue"
                  ? "✓"
                  : !unlocked
                    ? "🔒"
                    : ""}
              </span>
            </button>
          );
        })}
      </div>
      <div className="journey-foot">Select a completed section to review or revise it.</div>
    </nav>
  );
}
