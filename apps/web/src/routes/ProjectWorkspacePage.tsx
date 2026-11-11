import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useProject } from "../hooks/useProjects";
import { useActOnJourneyItem, useContinueSection, useJourney } from "../hooks/useJourney";
import { JourneyRail } from "../components/JourneyRail";
import { AccordionGroup } from "../components/AccordionGroup";
import { Toast } from "../components/Toast";
import { useToast } from "../hooks/useToast";
import { useTaskTray } from "../hooks/useTaskTray";
import { TaskTray } from "../components/TaskTray";
import { StudioToolsMenu } from "../components/StudioToolsMenu";
import type { ToolKey } from "../lib/studioTools";
import { StudioToolPanel } from "../components/StudioToolPanel";
import { AssetsTool } from "../components/tools/AssetsTool";
import { ScriptIntelligenceTool } from "../components/tools/ScriptIntelligenceTool";
import { ReviewTool } from "../components/tools/ReviewTool";
import { HistoricalResearchTool } from "../components/tools/HistoricalResearchTool";
import { StoryboardTool } from "../components/tools/StoryboardTool";
import { FilmBibleTool } from "../components/tools/FilmBibleTool";
import { AuditTool } from "../components/tools/AuditTool";
import type { JourneyItemAction, JourneySection } from "../api/client";
import { describeError } from "../lib/describeError";

const TOOL_TITLES: Record<ToolKey, { title: string; subtitle: string }> = {
  assets: { title: "Assets", subtitle: "Upload screenplays into private, immutable storage." },
  script_intelligence: {
    title: "Script Intelligence",
    subtitle: "Extract scenes, characters and locations from the screenplay.",
  },
  review: { title: "Candidate Review", subtitle: "Approve or reject AI-extracted candidates before they become canon." },
  historical_research: {
    title: "Historical Research",
    subtitle: "Investigate, record and verify historical evidence.",
  },
  storyboard: { title: "Storyboard", subtitle: "Generate and review the visual shot sequence." },
  film_bible: { title: "Film Bible", subtitle: "Canonical visual-world rules, scenes and entities." },
  audit: { title: "Audit Trail", subtitle: "Every project lifecycle action and decision." },
};

/** The server is authoritative on `can_continue`; this local pick only decides which
 * section opens by default -- the first one not yet past the gate, or the last one if
 * every section has already been continued. */
function defaultSectionId(sections: JourneySection[]): string | undefined {
  const first = sections.find((s) => s.status !== "completed" && s.status !== "ready_to_continue");
  return (first ?? sections[sections.length - 1])?.id;
}

/** Mirrors the wireframe's `sectionProgress()`: progress counts only required, applicable
 * groups, and a group counts as "done" once it is completed or (legitimately) marked not
 * applicable. */
function sectionProgress(section: JourneySection) {
  const required = section.groups.filter((g) => g.required && g.applies);
  const done = required.filter((g) => g.status === "completed" || g.status === "not_applicable").length;
  const total = required.length;
  return { done, total, pct: total ? Math.round((done / total) * 100) : 100 };
}

function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));
  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);
  return online;
}

export function ProjectWorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const project = useProject(projectId);
  const journey = useJourney(projectId);
  const actOnItem = useActOnJourneyItem(projectId ?? "");
  const continueSection = useContinueSection(projectId ?? "");
  const { message, showToast } = useToast();
  const isOnline = useOnlineStatus();
  const taskTray = useTaskTray();
  const [openTool, setOpenTool] = useState<ToolKey | null>(null);

  const sections = journey.data ?? [];
  const [openGroupIds, setOpenGroupIds] = useState<Set<string>>(new Set());
  const [pendingSubpointId, setPendingSubpointId] = useState<string | null>(null);

  // The user's explicit pick, when it still names a real section; otherwise derive one
  // on the fly. Deriving this at render time (rather than syncing it via an effect) means
  // a pick that becomes stale -- the section it named disappearing, or everything above
  // it completing -- resolves immediately on the next render instead of flashing the old
  // selection for a tick.
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const activeSectionId =
    selectedSectionId && sections.some((s) => s.id === selectedSectionId)
      ? selectedSectionId
      : defaultSectionId(sections);

  const activeSection = sections.find((s) => s.id === activeSectionId);
  const activeIndex = sections.findIndex((s) => s.id === activeSectionId);

  function selectSection(sectionId: string) {
    setSelectedSectionId(sectionId);
    setOpenGroupIds(new Set());
  }

  function toggleGroup(groupId: string) {
    setOpenGroupIds((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  }

  async function handleAct(jrnId: string, action: JourneyItemAction) {
    setPendingSubpointId(jrnId);
    try {
      await actOnItem.mutateAsync({ jrnId, action });
      if (action.action === "not_applicable") showToast("Marked not applicable.");
      else if (action.action === "draft") showToast("Draft saved.");
      else if (action.action === "request_review") showToast("Sent for review.");
      else showToast("Marked complete.");
    } catch (err) {
      showToast(describeError(err));
    } finally {
      setPendingSubpointId(null);
    }
  }

  async function handleContinue() {
    if (!activeSection) return;
    try {
      await continueSection.mutateAsync(activeSection.id);
      showToast("Section complete. Moving to the next stage.");
      const next = sections[activeIndex + 1];
      if (next) selectSection(next.id);
    } catch (err) {
      showToast(describeError(err));
    }
  }

  if (!projectId) {
    return <div className="state-panel error">No project selected.</div>;
  }

  if (project.isLoading || journey.isLoading) {
    return <div className="state-panel">Loading project workspace…</div>;
  }

  if (project.isError || journey.isError) {
    const err = project.error ?? journey.error;
    return (
      <div className="state-panel error" role="alert">
        Could not load this project. {describeError(err)}
      </div>
    );
  }

  if (!project.data || sections.length === 0) {
    return <div className="state-panel">This project has no journey data yet.</div>;
  }

  const currentProject = project.data;
  const progress = activeSection ? sectionProgress(activeSection) : { done: 0, total: 0, pct: 100 };

  return (
    <div className="project-shell">
      <JourneyRail
        project={currentProject}
        sections={sections}
        activeSectionId={activeSectionId ?? sections[0].id}
        onSelectSection={selectSection}
      />
      <main className="project-main">
        {!isOnline && (
          <div className="state-panel error" role="status" style={{ marginBottom: 14 }}>
            You're offline. Changes can't be saved until your connection comes back.
          </div>
        )}

        <div className="crumb">
          Online Workspace / {currentProject.title} /{" "}
          <b>{activeSection ? activeSection.title : ""}</b>
        </div>

        <div className="project-top">
          <div>
            <div className="eyebrow">{currentProject.production_mode.replace(/_/g, " ").toUpperCase()}</div>
            <h1>{currentProject.title}</h1>
            <p>{currentProject.logline || "No logline set yet."}</p>
          </div>
          <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
            <StudioToolsMenu activeSectionId={activeSectionId ?? sections[0].id} onOpenTool={setOpenTool} />
            <button type="button" className="btn" onClick={() => showToast("Project settings aren't built yet.")}>
              Project Settings
            </button>
          </div>
        </div>
        <div className="project-meta">
          <span className="tag">{currentProject.genre || "Unspecified genre"}</span>
          <span className="tag amber">{currentProject.production_mode.replace(/_/g, " ")}</span>
          <span className="tag">{currentProject.status}</span>
          <span className="tag">v{currentProject.current_version}</span>
        </div>

        {activeSection && (
          <>
            <div className="section-progress">
              <div className="section-progress-top">
                <span>Current section progress</span>
                <b>
                  {progress.done} / {progress.total} required
                </b>
              </div>
              <div className="progress">
                <span style={{ width: `${progress.pct}%` }} />
              </div>
            </div>

            <div className="stage-intro">
              <div>
                <div className="eyebrow">{activeSection.release_label}</div>
                <h2>{activeSection.title}</h2>
                <p>Complete the groups below. Opening a group does not count as completing it.</p>
              </div>
              <div className="stage-actions">
                <button
                  type="button"
                  className="btn small"
                  onClick={() => setOpenGroupIds(new Set(activeSection.groups.map((g) => g.id)))}
                >
                  Expand all
                </button>
                <button type="button" className="btn small" onClick={() => setOpenGroupIds(new Set())}>
                  Collapse all
                </button>
              </div>
            </div>

            {activeSection.groups.length === 0 ? (
              <div className="state-panel">Nothing to show for this section yet.</div>
            ) : (
              <div className="accordion-list">
                {activeSection.groups.map((group, index) => (
                  <AccordionGroup
                    key={group.id}
                    group={group}
                    index={index + 1}
                    isOpen={openGroupIds.has(group.id)}
                    onToggle={() => toggleGroup(group.id)}
                    onAct={handleAct}
                    pendingSubpointId={pendingSubpointId}
                  />
                ))}
              </div>
            )}

            <div className="stage-gate">
              <div>
                <h3>
                  {activeSection.can_continue
                    ? "Ready to continue"
                    : "Complete the required work to continue"}
                </h3>
                <p>Complete required subpoints and approvals. Opening a screen does not count as completion.</p>
                <div className="gate-summary">
                  {progress.done} completed or not applicable · {progress.total - progress.done} remaining
                </div>
              </div>
              <button
                type="button"
                className="btn primary"
                disabled={!activeSection.can_continue || continueSection.isPending}
                onClick={handleContinue}
              >
                {continueSection.isPending ? "Continuing…" : "Continue to Next Section →"}
              </button>
            </div>
          </>
        )}
      </main>

      {openTool && (
        <StudioToolPanel
          title={TOOL_TITLES[openTool].title}
          subtitle={TOOL_TITLES[openTool].subtitle}
          onClose={() => setOpenTool(null)}
        >
          {openTool === "assets" && <AssetsTool projectId={projectId} />}
          {openTool === "script_intelligence" && (
            <ScriptIntelligenceTool projectId={projectId} onRunStarted={taskTray.trackRun} />
          )}
          {openTool === "review" && <ReviewTool projectId={projectId} />}
          {openTool === "historical_research" && (
            <HistoricalResearchTool projectId={projectId} onRunStarted={taskTray.trackRun} />
          )}
          {openTool === "storyboard" && <StoryboardTool projectId={projectId} onRunStarted={taskTray.trackRun} />}
          {openTool === "film_bible" && <FilmBibleTool projectId={projectId} onRunStarted={taskTray.trackRun} />}
          {openTool === "audit" && <AuditTool projectId={projectId} />}
        </StudioToolPanel>
      )}

      <TaskTray tasks={taskTray.tasks} onDismiss={taskTray.dismiss} onOpenReview={() => setOpenTool("review")} />
      <Toast message={message} />
    </div>
  );
}
