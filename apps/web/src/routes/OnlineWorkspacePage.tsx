import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateProject, useProjects, useProjectTemplates } from "../hooks/useProjects";
import { ApiError, type ProductionMode } from "../api/client";

const PRODUCTION_MODES: { value: ProductionMode; label: string }[] = [
  { value: "mixed", label: "Mixed (both AI and live-action)" },
  { value: "fully_ai", label: "Fully AI-generated" },
  { value: "hybrid_live_action", label: "Hybrid live-action + AI" },
];

export function OnlineWorkspacePage() {
  const [includeArchived, setIncludeArchived] = useState(false);
  const projects = useProjects(includeArchived);
  const templates = useProjectTemplates();
  const createProject = useCreateProject();
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") ?? "").trim();
    if (!title) return;
    const formatTemplateKey = String(form.get("format_template_key") ?? "");
    const project = await createProject.mutateAsync({
      title,
      logline: String(form.get("logline") ?? "") || undefined,
      genre: String(form.get("genre") ?? "") || undefined,
      production_mode: String(form.get("production_mode") ?? "mixed") as ProductionMode,
      format_template_key: formatTemplateKey || undefined,
    });
    navigate(`/projects/${project.id}`);
  }

  return (
    <main className="workspace-page">
      <div className="page-top">
        <div>
          <div className="eyebrow">Online Workspace</div>
          <h1>Your projects</h1>
          <p>Create a new project or continue one already in progress.</p>
        </div>
      </div>

      <div className="workspace-grid">
        <section className="card" aria-label="Projects">
          <div className="card-head">
            <h2>Projects</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <label style={{ fontSize: 12, display: "flex", gap: 4, alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={includeArchived}
                  onChange={(e) => setIncludeArchived(e.target.checked)}
                />
                Show archived
              </label>
              <button type="button" className="btn gold small" onClick={() => setShowForm((v) => !v)}>
                {showForm ? "Cancel" : "+ New project"}
              </button>
            </div>
          </div>
          <div className="card-body">
            {showForm && (
              <form onSubmit={onCreate} style={{ marginBottom: 16 }}>
                <input
                  name="title"
                  aria-label="Project title"
                  placeholder="Project title"
                  required
                  style={{
                    width: "100%",
                    padding: 10,
                    marginBottom: 8,
                    borderRadius: 8,
                    border: "1px solid var(--line)",
                  }}
                />
                <input
                  name="logline"
                  aria-label="Logline"
                  placeholder="Logline (optional)"
                  style={{
                    width: "100%",
                    padding: 10,
                    marginBottom: 8,
                    borderRadius: 8,
                    border: "1px solid var(--line)",
                  }}
                />
                <input
                  name="genre"
                  aria-label="Genre"
                  placeholder="Genre (optional)"
                  style={{
                    width: "100%",
                    padding: 10,
                    marginBottom: 8,
                    borderRadius: 8,
                    border: "1px solid var(--line)",
                  }}
                />
                <select
                  name="production_mode"
                  aria-label="Production mode"
                  defaultValue="mixed"
                  style={{
                    width: "100%",
                    padding: 10,
                    marginBottom: 8,
                    borderRadius: 8,
                    border: "1px solid var(--line)",
                  }}
                >
                  {PRODUCTION_MODES.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
                <select
                  name="format_template_key"
                  aria-label="Format template"
                  defaultValue=""
                  disabled={templates.isLoading}
                  style={{
                    width: "100%",
                    padding: 10,
                    marginBottom: 12,
                    borderRadius: 8,
                    border: "1px solid var(--line)",
                  }}
                >
                  <option value="">Format: decide later</option>
                  {templates.data?.map((t) => (
                    <option key={t.key} value={t.key}>
                      {t.name}
                    </option>
                  ))}
                </select>
                {createProject.isError && (
                  <p role="alert" style={{ color: "var(--red)", fontSize: 12 }}>
                    {createProject.error instanceof ApiError
                      ? createProject.error.message
                      : "Could not create the project."}
                  </p>
                )}
                <button type="submit" className="btn primary" disabled={createProject.isPending}>
                  {createProject.isPending ? "Creating…" : "Create project"}
                </button>
              </form>
            )}

            {projects.isLoading && <div className="state-panel">Loading projects…</div>}
            {projects.isError && (
              <div className="state-panel error" role="alert">
                Could not load your projects.{" "}
                {projects.error instanceof ApiError ? projects.error.message : ""}
              </div>
            )}
            {projects.data && projects.data.length === 0 && !showForm && (
              <div className="state-panel">
                No projects yet. Create your first one to start the guided workflow.
              </div>
            )}
            {projects.data && projects.data.length > 0 && (
              <div className="project-grid">
                {projects.data.map((project) => (
                  <button
                    key={project.id}
                    type="button"
                    className="project-card"
                    onClick={() => navigate(`/projects/${project.id}`)}
                  >
                    <div className="project-thumb">
                      <b>{project.title}</b>
                    </div>
                    <div className="project-content">
                      <p>{project.logline || "No logline yet."}</p>
                      <div className="project-line">
                        <span>{project.genre || "Unspecified genre"}</span>
                        <span>v{project.current_version}</span>
                      </div>
                      <div className="tagrow" style={{ display: "flex", gap: 5 }}>
                        <span className="tag amber">{project.production_mode.replace(/_/g, " ")}</span>
                        <span className="tag">{project.status}</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        <aside className="card" aria-label="Recent activity">
          <div className="card-head">
            <h3>Recent activity</h3>
          </div>
          <div className="card-body">
            <div className="state-panel">Activity across projects isn't built yet.</div>
          </div>
        </aside>
      </div>
    </main>
  );
}
