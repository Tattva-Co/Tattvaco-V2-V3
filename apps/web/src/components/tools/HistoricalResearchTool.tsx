import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  useCreateResearchQuestion,
  useCreateResearchSource,
  useResearchClaims,
  useResearchConflicts,
  useResearchQuestions,
  useResearchSources,
} from "../../hooks/useResearch";
import { describeError } from "../../lib/describeError";

const TABS = ["Investigate", "Questions", "Sources", "Claims", "Conflicts"] as const;
type Tab = (typeof TABS)[number];

const TIER_LABELS: Record<string, string> = {
  tier_0_project: "Tier 0 (Project material)",
  tier_1_primary: "Tier 1 (Primary / archaeological)",
  tier_2_scholarly: "Tier 2 (Scholarly secondary)",
  tier_3_discovery: "Tier 3 (Discovery / unverified)",
};

function InvestigateTab({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const [topic, setTopic] = useState("");
  const [seedText, setSeedText] = useState("");
  const trigger = useMutation({
    mutationFn: () => api.workflows.triggerHistoricalResearch(projectId, topic.trim(), seedText.trim() || undefined),
    onSuccess: (result) => onRunStarted(result.workflow_run_id, `Historical research: ${topic.trim()}`),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (topic.trim()) trigger.mutate();
  }

  return (
    <form className="tool-form" onSubmit={onSubmit}>
      <p className="sub-desc">
        Retrieves primary/scholarly sources, extracts claims with locators, and flags contested interpretations.
      </p>
      <label htmlFor="research-topic">Investigation topic</label>
      <input id="research-topic" value={topic} onChange={(e) => setTopic(e.target.value)} required />
      <label htmlFor="research-seed">Director notes (optional)</label>
      <textarea id="research-seed" value={seedText} onChange={(e) => setSeedText(e.target.value)} />
      <button type="submit" className="btn primary" disabled={!topic.trim() || trigger.isPending}>
        {trigger.isPending ? "Starting…" : "Run historical investigation"}
      </button>
      {trigger.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
          {describeError(trigger.error)}
        </p>
      )}
      {trigger.isSuccess && <p style={{ color: "var(--green)", fontSize: 11 }}>Started -- watch the task tray.</p>}
    </form>
  );
}

function QuestionsTab({ projectId }: { projectId: string }) {
  const questions = useResearchQuestions(projectId);
  const createQuestion = useCreateResearchQuestion(projectId);
  const [text, setText] = useState("");
  const [category, setCategory] = useState("general");

  return (
    <div>
      <form
        className="tool-form"
        style={{ marginBottom: 16 }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!text.trim()) return;
          createQuestion.mutate(
            { text: text.trim(), category },
            { onSuccess: () => setText("") }
          );
        }}
      >
        <label htmlFor="new-question-text">Propose a question</label>
        <input id="new-question-text" value={text} onChange={(e) => setText(e.target.value)} />
        <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Question category">
          {["general", "costume", "architecture", "military", "politics", "religion", "trade"].map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <button type="submit" className="btn small" disabled={!text.trim() || createQuestion.isPending}>
          Add question
        </button>
      </form>
      {questions.isLoading && <div className="state-panel">Loading questions…</div>}
      {questions.data?.length === 0 && <div className="state-panel">No research questions logged yet.</div>}
      {questions.data?.map((q) => (
        <div key={q.id} className="tool-list-item">
          <h4>
            [{q.category}] {q.text}
          </h4>
          <div className="meta">
            Status: {q.status} · v{q.project_version}
          </div>
        </div>
      ))}
    </div>
  );
}

function SourcesTab({ projectId }: { projectId: string }) {
  const sources = useResearchSources(projectId);
  const createSource = useCreateResearchSource(projectId);
  const [title, setTitle] = useState("");
  const [tier, setTier] = useState("tier_2_scholarly");
  const [author, setAuthor] = useState("");
  const [locator, setLocator] = useState("");

  return (
    <div>
      <form
        className="tool-form"
        style={{ marginBottom: 16 }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!title.trim()) return;
          createSource.mutate(
            { title: title.trim(), tier, author: author.trim() || null, locator: locator.trim() || null },
            { onSuccess: () => setTitle("") }
          );
        }}
      >
        <label htmlFor="source-title">Register a source</label>
        <input id="source-title" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <select value={tier} onChange={(e) => setTier(e.target.value)} aria-label="Source tier">
          {Object.entries(TIER_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <input placeholder="Author (optional)" value={author} onChange={(e) => setAuthor(e.target.value)} aria-label="Author" />
        <input placeholder="Locator (optional)" value={locator} onChange={(e) => setLocator(e.target.value)} aria-label="Locator" />
        <button type="submit" className="btn small" disabled={!title.trim() || createSource.isPending}>
          Record source
        </button>
      </form>
      {sources.isLoading && <div className="state-panel">Loading sources…</div>}
      {sources.data?.length === 0 && <div className="state-panel">No sources recorded yet.</div>}
      {sources.data?.map((s) => (
        <div key={s.id} className="tool-list-item">
          <h4>{s.title}</h4>
          <p>{TIER_LABELS[s.tier] ?? s.tier}</p>
          <div className="meta">
            {s.author && `${s.author} · `}
            {s.locator && `${s.locator} · `}v{s.project_version}
          </div>
        </div>
      ))}
    </div>
  );
}

function ClaimsTab({ projectId }: { projectId: string }) {
  const claims = useResearchClaims(projectId);
  if (claims.isLoading) return <div className="state-panel">Loading claims…</div>;
  if (claims.data?.length === 0) return <div className="state-panel">No canonical claims committed yet.</div>;
  return (
    <div>
      {claims.data?.map((c) => (
        <div key={c.id} className="tool-list-item">
          <h4>
            [{c.claim_class}] {c.statement}
          </h4>
          <div className="meta">
            {c.era_or_date && `${c.era_or_date} · `}
            {c.location && `${c.location} · `}
            Confidence {Math.round(c.confidence * 100)}% · v{c.project_version}
          </div>
        </div>
      ))}
    </div>
  );
}

function ConflictsTab({ projectId }: { projectId: string }) {
  const conflicts = useResearchConflicts(projectId);
  if (conflicts.isLoading) return <div className="state-panel">Loading conflicts…</div>;
  if (conflicts.data?.length === 0) return <div className="state-panel">No open historical conflicts flagged.</div>;
  return (
    <div>
      {conflicts.data?.map((c) => (
        <div key={c.id} className="tool-list-item">
          <p>{c.description}</p>
          {c.resolution_notes && <p className="meta">Resolution stance: {c.resolution_notes}</p>}
          <div className="meta">
            Status: {c.status} · v{c.project_version}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Maps to JRN-03.2 - JRN-03.6 (Research & Story Intelligence). */
export function HistoricalResearchTool({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("Investigate");
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
      {tab === "Investigate" && <InvestigateTab projectId={projectId} onRunStarted={onRunStarted} />}
      {tab === "Questions" && <QuestionsTab projectId={projectId} />}
      {tab === "Sources" && <SourcesTab projectId={projectId} />}
      {tab === "Claims" && <ClaimsTab projectId={projectId} />}
      {tab === "Conflicts" && <ConflictsTab projectId={projectId} />}
    </div>
  );
}
