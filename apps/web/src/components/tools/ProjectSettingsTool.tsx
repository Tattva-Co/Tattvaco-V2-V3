import { useState } from "react";
import type { Project, ProductionMode, ProjectScale, QualityProfile } from "../../api/client";
import {
  useArchiveProject,
  useCreateEpisode,
  useCreateOutputProfile,
  useDeleteOutputProfile,
  useEpisodes,
  useOutputProfiles,
  useProjectTemplates,
  useUpdateOutputProfile,
  useUpdateProject,
} from "../../hooks/useProjects";
import { describeError } from "../../lib/describeError";

const TABS = ["Metadata", "Output Profiles", "Episodes"] as const;
type Tab = (typeof TABS)[number];

const PRODUCTION_MODES = ["fully_ai", "hybrid_live_action", "mixed"] as const;
const QUALITY_PROFILES = ["draft", "standard", "premium"] as const;
const PROJECT_SCALES = ["small", "medium", "large"] as const;

function MetadataTab({ project }: { project: Project }) {
  const update = useUpdateProject(project.id);
  const archive = useArchiveProject(project.id);
  const templates = useProjectTemplates();

  const [title, setTitle] = useState(project.title);
  const [logline, setLogline] = useState(project.logline ?? "");
  const [genre, setGenre] = useState(project.genre ?? "");
  const [productionMode, setProductionMode] = useState<ProductionMode>(
    project.production_mode as ProductionMode
  );
  const [formatTemplateKey, setFormatTemplateKey] = useState(project.format_template_key ?? "");
  const [qualityProfile, setQualityProfile] = useState<QualityProfile | "">(
    (project.quality_profile as QualityProfile | null) ?? ""
  );
  const [scale, setScale] = useState<ProjectScale | "">((project.scale as ProjectScale | null) ?? "");

  function save() {
    update.mutate({
      title,
      logline: logline || null,
      genre: genre || null,
      production_mode: productionMode,
      format_template_key: formatTemplateKey || null,
      quality_profile: qualityProfile || null,
      scale: scale || null,
    });
  }

  return (
    <div className="tool-form">
      <label htmlFor="settings-title">Title</label>
      <input id="settings-title" value={title} onChange={(e) => setTitle(e.target.value)} />

      <label htmlFor="settings-logline">Logline</label>
      <input id="settings-logline" value={logline} onChange={(e) => setLogline(e.target.value)} />

      <label htmlFor="settings-genre">Genre</label>
      <input id="settings-genre" value={genre} onChange={(e) => setGenre(e.target.value)} />

      <label htmlFor="settings-mode">Production mode</label>
      <select
        id="settings-mode"
        value={productionMode}
        onChange={(e) => setProductionMode(e.target.value as ProductionMode)}
      >
        {PRODUCTION_MODES.map((m) => (
          <option key={m} value={m}>
            {m.replace(/_/g, " ")}
          </option>
        ))}
      </select>

      <label htmlFor="settings-template">Format template</label>
      <select
        id="settings-template"
        value={formatTemplateKey}
        onChange={(e) => setFormatTemplateKey(e.target.value)}
        disabled={templates.isLoading}
      >
        <option value="">Decide later</option>
        {templates.data?.map((t) => (
          <option key={t.key} value={t.key}>
            {t.name}
          </option>
        ))}
      </select>

      <label htmlFor="settings-quality">Visual quality profile</label>
      <select
        id="settings-quality"
        value={qualityProfile}
        onChange={(e) => setQualityProfile(e.target.value as QualityProfile | "")}
      >
        <option value="">Decide later</option>
        {QUALITY_PROFILES.map((q) => (
          <option key={q} value={q}>
            {q}
          </option>
        ))}
      </select>

      <label htmlFor="settings-scale">Project scale</label>
      <select id="settings-scale" value={scale} onChange={(e) => setScale(e.target.value as ProjectScale | "")}>
        <option value="">Decide later</option>
        {PROJECT_SCALES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <button type="button" className="btn primary small" disabled={update.isPending} onClick={save}>
        {update.isPending ? "Saving…" : "Save settings"}
      </button>
      {update.isError && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
          {describeError(update.error)}
        </p>
      )}

      <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--line)" }}>
        <p className="meta" style={{ marginBottom: 8 }}>
          {project.status === "archived"
            ? "This project is archived -- hidden from the default project list."
            : "Archiving hides this project from the default list. It can be restored at any time."}
        </p>
        <button
          type="button"
          className="btn small"
          disabled={archive.isPending}
          onClick={() => archive.mutate(project.status !== "archived")}
        >
          {project.status === "archived" ? "Unarchive project" : "Archive project"}
        </button>
      </div>
    </div>
  );
}

function OutputProfilesTab({ projectId }: { projectId: string }) {
  const profiles = useOutputProfiles(projectId);
  const createProfile = useCreateOutputProfile(projectId);
  const updateProfile = useUpdateOutputProfile(projectId);
  const deleteProfile = useDeleteOutputProfile(projectId);
  const [name, setName] = useState("");
  const [resolution, setResolution] = useState("");
  const [aspectRatio, setAspectRatio] = useState("");

  return (
    <div>
      <form
        className="tool-form"
        style={{ marginBottom: 16 }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          createProfile.mutate(
            {
              name: name.trim(),
              resolution: resolution || null,
              aspect_ratio: aspectRatio || null,
              subtitles_required: false,
              is_default: false,
            },
            {
              onSuccess: () => {
                setName("");
                setResolution("");
                setAspectRatio("");
              },
            }
          );
        }}
      >
        <label htmlFor="profile-name">Add an output/delivery profile</label>
        <input id="profile-name" placeholder="e.g. 16:9 Master" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="Resolution (e.g. 3840x2160)" value={resolution} onChange={(e) => setResolution(e.target.value)} />
        <input placeholder="Aspect ratio (e.g. 16:9)" value={aspectRatio} onChange={(e) => setAspectRatio(e.target.value)} />
        <button type="submit" className="btn small" disabled={!name.trim() || createProfile.isPending}>
          Add profile
        </button>
      </form>

      {profiles.isLoading && <div className="state-panel">Loading output profiles…</div>}
      {profiles.data?.length === 0 && <div className="state-panel">No output profiles yet.</div>}
      {profiles.data?.map((p) => (
        <div key={p.id} className="tool-list-item">
          <h4>
            {p.name} {p.is_default && <span className="tag">default</span>}
          </h4>
          <p className="meta">
            {p.resolution ?? "—"} · {p.aspect_ratio ?? "—"} · {p.delivery_format ?? "format TBD"}
          </p>
          <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
            {!p.is_default && (
              <button
                type="button"
                className="tiny-btn"
                onClick={() => updateProfile.mutate({ profileId: p.id, body: { is_default: true } })}
              >
                Make default
              </button>
            )}
            <button type="button" className="tiny-btn" onClick={() => deleteProfile.mutate(p.id)}>
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function EpisodesTab({ projectId }: { projectId: string }) {
  const episodes = useEpisodes(projectId);
  const createEpisode = useCreateEpisode(projectId);
  const [episodeNumber, setEpisodeNumber] = useState("");
  const [title, setTitle] = useState("");

  return (
    <div>
      <form
        className="tool-form"
        style={{ marginBottom: 16 }}
        onSubmit={(e) => {
          e.preventDefault();
          const n = Number(episodeNumber);
          if (!n || n < 1) return;
          createEpisode.mutate(
            { episode_number: n, title: title.trim() || null },
            {
              onSuccess: () => {
                setEpisodeNumber("");
                setTitle("");
              },
            }
          );
        }}
      >
        <label htmlFor="episode-number">Add an episode</label>
        <input
          id="episode-number"
          type="number"
          min={1}
          placeholder="Episode number"
          value={episodeNumber}
          onChange={(e) => setEpisodeNumber(e.target.value)}
        />
        <input placeholder="Episode title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
        <button type="submit" className="btn small" disabled={!episodeNumber || createEpisode.isPending}>
          Add episode
        </button>
        {createEpisode.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(createEpisode.error)}
          </p>
        )}
      </form>

      {episodes.isLoading && <div className="state-panel">Loading episodes…</div>}
      {episodes.data?.length === 0 && (
        <div className="state-panel">No episodes yet -- only relevant for episodic formats (OTT series, etc.).</div>
      )}
      {episodes.data?.map((e) => (
        <div key={e.id} className="tool-list-item">
          <h4>
            Episode {e.episode_number}
            {e.title ? `: ${e.title}` : ""}
          </h4>
        </div>
      ))}
    </div>
  );
}

/** S-PRJ-02 Project Settings & Governance. */
export function ProjectSettingsTool({ project }: { project: Project }) {
  const [tab, setTab] = useState<Tab>("Metadata");
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
      {tab === "Metadata" && <MetadataTab project={project} />}
      {tab === "Output Profiles" && <OutputProfilesTab projectId={project.id} />}
      {tab === "Episodes" && <EpisodesTab projectId={project.id} />}
    </div>
  );
}
