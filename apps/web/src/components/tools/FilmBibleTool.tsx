import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  useCharacters,
  useCreateFilmBibleRule,
  useDialogueSegments,
  useEntities,
  useFilmBibleRules,
  useLocations,
  useProjectVersions,
  useScenes,
} from "../../hooks/useFilmBible";
import { describeError } from "../../lib/describeError";

const TABS = [
  "Visual World Rules",
  "Synthesize",
  "Scenes",
  "Dialogue",
  "Entities",
  "Characters",
  "Locations",
  "Versions",
] as const;
type Tab = (typeof TABS)[number];

const CATEGORY_LABELS: Record<string, string> = {
  tone_aesthetic: "Tone & aesthetic direction",
  color_palette: "Color palette & pigment strategy",
  lighting_atmosphere: "Lighting & atmosphere",
  architectural_environment: "Architecture & spatial rules",
  material_culture: "Material culture, garments & arms",
  camera_language: "Camera language & grammar",
};

function RulesTab({ projectId }: { projectId: string }) {
  const rules = useFilmBibleRules(projectId);
  const createRule = useCreateFilmBibleRule(projectId);
  const [category, setCategory] = useState("tone_aesthetic");
  const [title, setTitle] = useState("");
  const [ruleText, setRuleText] = useState("");
  const [negGuidance, setNegGuidance] = useState("");
  const [strictness, setStrictness] = useState("guideline");

  return (
    <div>
      <form
        className="tool-form"
        style={{ marginBottom: 16 }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!title.trim() || !ruleText.trim()) return;
          createRule.mutate(
            {
              category,
              title: title.trim(),
              rule_text: ruleText.trim(),
              negative_prompt_guidance: negGuidance.trim() || null,
              strictness,
            },
            {
              onSuccess: () => {
                setTitle("");
                setRuleText("");
                setNegGuidance("");
              },
            }
          );
        }}
      >
        <label htmlFor="rule-category">Propose a manual visual rule</label>
        <select id="rule-category" value={category} onChange={(e) => setCategory(e.target.value)}>
          {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <input placeholder="Rule title" value={title} onChange={(e) => setTitle(e.target.value)} aria-label="Rule title" />
        <textarea
          placeholder="Rule description"
          value={ruleText}
          onChange={(e) => setRuleText(e.target.value)}
          aria-label="Rule description"
        />
        <input
          placeholder="Negative prompt guidance (optional)"
          value={negGuidance}
          onChange={(e) => setNegGuidance(e.target.value)}
          aria-label="Negative prompt guidance"
        />
        <select value={strictness} onChange={(e) => setStrictness(e.target.value)} aria-label="Strictness">
          <option value="mandatory">Mandatory (strict constraint)</option>
          <option value="guideline">Creative guideline</option>
          <option value="deliberate_deviation">Deliberate historical deviation</option>
        </select>
        <button type="submit" className="btn small" disabled={!title.trim() || !ruleText.trim() || createRule.isPending}>
          Add rule to canon
        </button>
        {createRule.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(createRule.error)}
          </p>
        )}
      </form>

      {rules.isLoading && <div className="state-panel">Loading visual world rules…</div>}
      {rules.data?.length === 0 && <div className="state-panel">No visual world rules committed yet.</div>}
      {rules.data?.map((r) => (
        <div key={r.id} className="tool-list-item">
          <h4>{r.title}</h4>
          <p className="meta">
            {CATEGORY_LABELS[r.category] ?? r.category} · {r.strictness} · v{r.project_version}
          </p>
          <p>{r.rule_text}</p>
          {r.negative_prompt_guidance && <p className="meta">Negative prompt: {r.negative_prompt_guidance}</p>}
        </div>
      ))}
    </div>
  );
}

function SynthesizeTab({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const [userNotes, setUserNotes] = useState("");
  const trigger = useMutation({
    mutationFn: () => api.workflows.triggerFilmBibleSynthesis(projectId, userNotes.trim() || undefined),
    onSuccess: (result) => onRunStarted(result.workflow_run_id, "Film Bible synthesis"),
  });

  return (
    <div className="tool-form">
      <p className="sub-desc">
        Reads approved scenes and research claims, synthesizes aesthetic rules, and checks for historical
        contradictions before opening a review gate.
      </p>
      <label htmlFor="film-bible-notes">Director aesthetic brief</label>
      <textarea id="film-bible-notes" value={userNotes} onChange={(e) => setUserNotes(e.target.value)} />
      <button type="button" className="btn primary" disabled={trigger.isPending} onClick={() => trigger.mutate()}>
        {trigger.isPending ? "Starting…" : "Run Film Bible synthesis"}
      </button>
      {trigger.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
          {describeError(trigger.error)}
        </p>
      )}
      {trigger.isSuccess && <p style={{ color: "var(--green)", fontSize: 11 }}>Started -- watch the task tray.</p>}
    </div>
  );
}

function ScenesTab({ projectId }: { projectId: string }) {
  const scenes = useScenes(projectId);
  if (scenes.isLoading) return <div className="state-panel">Loading scenes…</div>;
  if (scenes.data?.length === 0) return <div className="state-panel">No canonical scenes committed yet.</div>;
  return (
    <div>
      {scenes.data?.map((s) => (
        <div key={s.id} className="tool-list-item">
          <h4>
            Scene {s.scene_number}: {s.heading}
          </h4>
          <p className="meta">
            {s.setting} · {s.location_name} · {s.time_of_day} · v{s.project_version}
          </p>
          <p>{s.summary}</p>
          <p className="meta">Characters: {s.characters_present.join(", ") || "None"}</p>
        </div>
      ))}
    </div>
  );
}

function EntitiesTab({ projectId }: { projectId: string }) {
  const entities = useEntities(projectId);
  if (entities.isLoading) return <div className="state-panel">Loading entities…</div>;
  if (entities.data?.length === 0) return <div className="state-panel">No canonical entities committed yet.</div>;
  return (
    <div>
      {entities.data?.map((e) => (
        <div key={e.id} className="tool-list-item">
          <h4>
            [{e.category}] {e.name}
          </h4>
          {e.description && <p>{e.description}</p>}
          <p className="meta">v{e.project_version}</p>
        </div>
      ))}
    </div>
  );
}

/** S-SCR-02 AC2/AC3: dialogue is shown verbatim (byte-for-byte, no reformatting of
 * `line_text`/`parenthetical`) as structured, scene-grouped rows -- never raw JSON. */
function DialogueTab({ projectId }: { projectId: string }) {
  const scenes = useScenes(projectId);
  const dialogue = useDialogueSegments(projectId);
  if (scenes.isLoading || dialogue.isLoading) return <div className="state-panel">Loading dialogue…</div>;
  if (dialogue.data?.length === 0) return <div className="state-panel">No canonical dialogue committed yet.</div>;

  const sceneById = new Map((scenes.data ?? []).map((s) => [s.id, s]));
  const byScene = new Map<string, typeof dialogue.data>();
  for (const segment of dialogue.data ?? []) {
    const existing = byScene.get(segment.scene_id);
    if (existing) existing.push(segment);
    else byScene.set(segment.scene_id, [segment]);
  }

  return (
    <div>
      {[...byScene.entries()].map(([sceneId, segments]) => {
        const scene = sceneById.get(sceneId);
        return (
          <div key={sceneId} className="tool-list-item">
            <h4>{scene ? `Scene ${scene.scene_number}: ${scene.heading}` : "Scene"}</h4>
            {segments
              ?.slice()
              .sort((a, b) => a.order_in_scene - b.order_in_scene)
              .map((d) => (
                <p key={d.id}>
                  <strong>{d.character_name}</strong>
                  {d.parenthetical && <span className="meta"> ({d.parenthetical})</span>}
                  {d.line_text && <>: {d.line_text}</>}
                </p>
              ))}
          </div>
        );
      })}
    </div>
  );
}

function CharactersTab({ projectId }: { projectId: string }) {
  const characters = useCharacters(projectId);
  if (characters.isLoading) return <div className="state-panel">Loading characters…</div>;
  if (characters.data?.length === 0) return <div className="state-panel">No canonical characters resolved yet.</div>;
  return (
    <div>
      {characters.data?.map((c) => (
        <div key={c.id} className="tool-list-item">
          <h4>{c.canonical_name}</h4>
          {c.aliases.length > 0 && <p className="meta">Also known as: {c.aliases.join(", ")}</p>}
          <p className="meta">v{c.project_version}</p>
        </div>
      ))}
    </div>
  );
}

function LocationsTab({ projectId }: { projectId: string }) {
  const locations = useLocations(projectId);
  if (locations.isLoading) return <div className="state-panel">Loading locations…</div>;
  if (locations.data?.length === 0) return <div className="state-panel">No canonical locations resolved yet.</div>;
  return (
    <div>
      {locations.data?.map((l) => (
        <div key={l.id} className="tool-list-item">
          <h4>{l.canonical_name}</h4>
          {l.aliases.length > 0 && <p className="meta">Also known as: {l.aliases.join(", ")}</p>}
          <p className="meta">v{l.project_version}</p>
        </div>
      ))}
    </div>
  );
}

function VersionsTab({ projectId }: { projectId: string }) {
  const versions = useProjectVersions(projectId);
  if (versions.isLoading) return <div className="state-panel">Loading version history…</div>;
  return (
    <div>
      {versions.data?.map((v) => (
        <div key={v.id} className="tool-list-item">
          <h4>
            Version {v.version_number} ({v.branch_name})
          </h4>
          <p className="meta">
            {new Date(v.created_at).toLocaleString()} · {v.commit_message}
          </p>
        </div>
      ))}
    </div>
  );
}

/** Maps to JRN-05.1 (Film Bible & visual world). */
export function FilmBibleTool({
  projectId,
  onRunStarted,
}: {
  projectId: string;
  onRunStarted: (runId: string, label: string) => void;
}) {
  const [tab, setTab] = useState<Tab>("Visual World Rules");
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
      {tab === "Visual World Rules" && <RulesTab projectId={projectId} />}
      {tab === "Synthesize" && <SynthesizeTab projectId={projectId} onRunStarted={onRunStarted} />}
      {tab === "Scenes" && <ScenesTab projectId={projectId} />}
      {tab === "Dialogue" && <DialogueTab projectId={projectId} />}
      {tab === "Entities" && <EntitiesTab projectId={projectId} />}
      {tab === "Characters" && <CharactersTab projectId={projectId} />}
      {tab === "Locations" && <LocationsTab projectId={projectId} />}
      {tab === "Versions" && <VersionsTab projectId={projectId} />}
    </div>
  );
}
