/**
 * Thin, typed fetch wrapper over the generated OpenAPI types (src/api/schema.ts;
 * regenerate with `npm run generate-api-types` after a backend schema change).
 *
 * Deliberately not using a generic "typed fetch" library's runtime: the API surface is
 * small (26 routes) and every call site in this app already needs its own
 * error-to-UI-state mapping (ApiError below), so a thin wrapper keeps that mapping in
 * one place without adding a dependency whose generated call signatures would need
 * adapting anyway.
 */
import type { components } from "./schema";
import { getAccessToken, clearAccessToken } from "./auth";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** Raised specifically for 401s, so route guards can distinguish "not signed in" from
 * every other failure without string-matching ApiError.message. */
export class UnauthenticatedError extends ApiError {}

async function send<T>(method: string, path: string, body?: BodyInit, extraHeaders?: Record<string, string>): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = { ...extraHeaders };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(path, { method, headers, body });

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const data = text ? JSON.parse(text) : undefined;

  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : response.statusText;
    const code = typeof data?.error === "string" ? data.error : `HTTP_${response.status}`;
    if (response.status === 401) {
      clearAccessToken();
      throw new UnauthenticatedError(response.status, code, detail);
    }
    throw new ApiError(response.status, code, detail);
  }
  return data as T;
}

async function request<T>(method: string, path: string, body?: object): Promise<T> {
  return send<T>(method, path, body === undefined ? undefined : JSON.stringify(body), {
    "Content-Type": "application/json",
  });
}

/** For multipart uploads: no Content-Type header is set, so the browser fills in the
 * multipart boundary itself -- setting it manually on a FormData body produces a
 * malformed request the server can't parse. */
async function requestMultipart<T>(path: string, formData: FormData): Promise<T> {
  return send<T>("POST", path, formData);
}

// -- Schema-derived request/response aliases --------------------------------------

type Schemas = components["schemas"];
export type Project = Schemas["ProjectResponse"];
export type JourneySection = Schemas["JourneySectionResponse"];
export type JourneyGroup = Schemas["JourneyGroupResponse"];
export type JourneySubpoint = Schemas["JourneySubpointResponse"];
export type JourneyItemAction = Schemas["JourneyItemActionRequest"];
export type JourneySectionContinueResult = Schemas["JourneySectionContinueResponse"];
export type DevLoginResponse = Schemas["DevLoginResponse"];
export type WorkflowRun = Schemas["WorkflowRunResponse"];
export type ProjectCreateBody = Schemas["ProjectCreateRequest"];
export type ProjectVersion = Schemas["ProjectVersionResponse"];
export type AuditEvent = Schemas["AuditEventResponse"];
export type Asset = Schemas["AssetResponse"];
export type AssetUploadResult = Schemas["AssetUploadResponse"];
export type WorkflowTriggerResult = Schemas["WorkflowTriggerResponse"];
export type Candidates = Schemas["CandidatesResponse"];
export type Approval = Schemas["ApprovalResponse"];
export type ApprovalDecisionBody = Schemas["ApprovalDecisionRequest"];
export type ApprovalDecisionResult = Schemas["ApprovalDecisionResponse"];
export type Scene = Schemas["SceneResponse"];
export type Entity = Schemas["EntityResponse"];
export type DialogueSegment = Schemas["DialogueSegmentResponse"];
export type Character = Schemas["CharacterResponse"];
export type Location = Schemas["LocationResponse"];
export type ResearchQuestion = Schemas["ResearchQuestionResponse"];
export type ResearchQuestionCreateBody = Schemas["ResearchQuestionCreateRequest"];
export type ResearchSource = Schemas["ResearchSourceResponse"];
export type ResearchSourceCreateBody = Schemas["ResearchSourceCreateRequest"];
export type ResearchClaim = Schemas["ResearchClaimResponse"];
export type ResearchConflict = Schemas["ResearchConflictResponse"];
export type StoryboardPanel = Schemas["StoryboardPanelResponse"];
export type FilmBibleRule = Schemas["FilmBibleRuleResponse"];
export type FilmBibleRuleCreateBody = Schemas["FilmBibleRuleCreateRequest"];
export type ProjectUpdateBody = Schemas["ProjectUpdateRequest"];
export type ProductionMode = Schemas["ProductionMode"];
export type QualityProfile = Schemas["QualityProfile"];
export type ProjectScale = Schemas["ProjectScale"];
export type FormatTemplate = Schemas["FormatTemplateResponse"];
export type OutputProfile = Schemas["OutputProfileResponse"];
export type OutputProfileCreateBody = Schemas["OutputProfileCreateRequest"];
export type OutputProfileUpdateBody = Schemas["OutputProfileUpdateRequest"];
export type Episode = Schemas["EpisodeResponse"];
export type EpisodeCreateBody = Schemas["EpisodeCreateRequest"];
export type RoleTemplate = Schemas["RoleTemplateResponse"];
export type ProjectMember = Schemas["ProjectMemberResponse"];
export type ProjectMemberAddBody = Schemas["ProjectMemberAddRequest"];
export type ProjectMemberRoleUpdateBody = Schemas["ProjectMemberRoleUpdateRequest"];
export type ProjectSummary = Schemas["ProjectSummaryResponse"];
export type ScreenplayVersion = Schemas["ScreenplayVersionResponse"];
export type ScreenplayVersionImportBody = Schemas["ScreenplayVersionImportRequest"];
export type ScreenplayVersionUpdateBody = Schemas["ScreenplayVersionUpdateRequest"];
export type ScreenplayDiff = Schemas["ScreenplayDiffResponse"];
export type ScreenplayDecisionBody = Schemas["ScreenplayDecisionRequest"];
export type ScreenplayDecisionResult = Schemas["ScreenplayDecisionResponse"];
export type ScreenplaySuggestion = Schemas["ScreenplaySuggestionResponse"];
export type ScreenplaySuggestionGenerateBody = Schemas["ScreenplaySuggestionGenerateRequest"];
export type ScreenplaySuggestionDecisionBody = Schemas["ScreenplaySuggestionDecisionRequest"];
export type ImpactAnalysis = Schemas["ImpactAnalysisResponse"];
export type ImpactPreview = Schemas["ImpactPreviewResponse"];

export const api = {
  auth: {
    devLogin: (email: string, fullName?: string) =>
      request<DevLoginResponse>("POST", "/api/v1/auth/dev-login", { email, full_name: fullName }),
  },
  projects: {
    list: (includeArchived = false) =>
      request<Project[]>("GET", `/api/v1/projects${includeArchived ? "?include_archived=true" : ""}`),
    get: (id: string) => request<Project>("GET", `/api/v1/projects/${id}`),
    create: (body: ProjectCreateBody) => request<Project>("POST", "/api/v1/projects", body),
    update: (id: string, body: ProjectUpdateBody) => request<Project>("PATCH", `/api/v1/projects/${id}`, body),
    archive: (id: string) => request<Project>("POST", `/api/v1/projects/${id}/archive`),
    unarchive: (id: string) => request<Project>("POST", `/api/v1/projects/${id}/unarchive`),
    summary: (id: string) => request<ProjectSummary>("GET", `/api/v1/projects/${id}/summary`),
    versions: (id: string) => request<ProjectVersion[]>("GET", `/api/v1/projects/${id}/versions`),
    auditLog: (id: string) => request<AuditEvent[]>("GET", `/api/v1/projects/${id}/audit-log`),
    scenes: (id: string) => request<Scene[]>("GET", `/api/v1/projects/${id}/scenes`),
    entities: (id: string) => request<Entity[]>("GET", `/api/v1/projects/${id}/entities`),
    dialogueSegments: (id: string) => request<DialogueSegment[]>("GET", `/api/v1/projects/${id}/dialogue-segments`),
    characters: (id: string) => request<Character[]>("GET", `/api/v1/projects/${id}/characters`),
    locations: (id: string) => request<Location[]>("GET", `/api/v1/projects/${id}/locations`),
  },
  projectTemplates: {
    list: () => request<FormatTemplate[]>("GET", "/api/v1/project-templates"),
  },
  outputProfiles: {
    list: (projectId: string) => request<OutputProfile[]>("GET", `/api/v1/projects/${projectId}/output-profiles`),
    create: (projectId: string, body: OutputProfileCreateBody) =>
      request<OutputProfile>("POST", `/api/v1/projects/${projectId}/output-profiles`, body),
    update: (projectId: string, profileId: string, body: OutputProfileUpdateBody) =>
      request<OutputProfile>("PATCH", `/api/v1/projects/${projectId}/output-profiles/${profileId}`, body),
    delete: (projectId: string, profileId: string) =>
      request<void>("DELETE", `/api/v1/projects/${projectId}/output-profiles/${profileId}`),
  },
  episodes: {
    list: (projectId: string) => request<Episode[]>("GET", `/api/v1/projects/${projectId}/episodes`),
    create: (projectId: string, body: EpisodeCreateBody) =>
      request<Episode>("POST", `/api/v1/projects/${projectId}/episodes`, body),
  },
  members: {
    roleTemplates: (projectId: string) =>
      request<RoleTemplate[]>("GET", `/api/v1/projects/${projectId}/role-templates`),
    list: (projectId: string) => request<ProjectMember[]>("GET", `/api/v1/projects/${projectId}/members`),
    add: (projectId: string, body: ProjectMemberAddBody) =>
      request<ProjectMember>("POST", `/api/v1/projects/${projectId}/members`, body),
    updateRole: (projectId: string, userId: string, body: ProjectMemberRoleUpdateBody) =>
      request<ProjectMember>("PATCH", `/api/v1/projects/${projectId}/members/${userId}`, body),
    remove: (projectId: string, userId: string) =>
      request<void>("DELETE", `/api/v1/projects/${projectId}/members/${userId}`),
  },
  assets: {
    list: (projectId: string) => request<Asset[]>("GET", `/api/v1/projects/${projectId}/assets`),
    upload: (projectId: string, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return requestMultipart<AssetUploadResult>(`/api/v1/projects/${projectId}/assets/upload`, formData);
    },
  },
  candidates: {
    get: (projectId: string) => request<Candidates>("GET", `/api/v1/projects/${projectId}/candidates`),
  },
  approvals: {
    decide: (approvalId: string, body: ApprovalDecisionBody) =>
      request<ApprovalDecisionResult>("POST", `/api/v1/approvals/${approvalId}/decide`, body),
  },
  research: {
    questions: {
      list: (projectId: string) => request<ResearchQuestion[]>("GET", `/api/v1/projects/${projectId}/research/questions`),
      create: (projectId: string, body: ResearchQuestionCreateBody) =>
        request<ResearchQuestion>("POST", `/api/v1/projects/${projectId}/research/questions`, body),
    },
    sources: {
      list: (projectId: string) => request<ResearchSource[]>("GET", `/api/v1/projects/${projectId}/research/sources`),
      create: (projectId: string, body: ResearchSourceCreateBody) =>
        request<ResearchSource>("POST", `/api/v1/projects/${projectId}/research/sources`, body),
    },
    claims: {
      list: (projectId: string) => request<ResearchClaim[]>("GET", `/api/v1/projects/${projectId}/research/claims`),
    },
    conflicts: {
      list: (projectId: string) => request<ResearchConflict[]>("GET", `/api/v1/projects/${projectId}/research/conflicts`),
    },
  },
  storyboard: {
    panels: (projectId: string) => request<StoryboardPanel[]>("GET", `/api/v1/projects/${projectId}/storyboard/panels`),
  },
  filmBible: {
    rules: {
      list: (projectId: string) => request<FilmBibleRule[]>("GET", `/api/v1/projects/${projectId}/film-bible/rules`),
      create: (projectId: string, body: FilmBibleRuleCreateBody) =>
        request<FilmBibleRule>("POST", `/api/v1/projects/${projectId}/film-bible/rules`, body),
    },
  },
  workflows: {
    triggerScriptIntelligence: (projectId: string, screenplayVersionId: string) =>
      request<WorkflowTriggerResult>("POST", `/api/v1/projects/${projectId}/workflows/script-intelligence`, {
        screenplay_version_id: screenplayVersionId,
      }),
    triggerHistoricalResearch: (projectId: string, topic: string, seedText?: string) =>
      request<WorkflowTriggerResult>("POST", `/api/v1/projects/${projectId}/workflows/historical-research`, {
        topic,
        seed_text: seedText ?? null,
      }),
    triggerStoryboardIntelligence: (projectId: string, brief?: string) =>
      request<WorkflowTriggerResult>("POST", `/api/v1/projects/${projectId}/workflows/storyboard-intelligence`, {
        brief: brief ?? null,
      }),
    triggerFilmBibleSynthesis: (projectId: string, userNotes?: string) =>
      request<WorkflowTriggerResult>("POST", `/api/v1/projects/${projectId}/workflows/film-bible-synthesis`, {
        user_notes: userNotes ?? null,
      }),
  },
  journey: {
    get: (projectId: string) => request<JourneySection[]>("GET", `/api/v1/projects/${projectId}/journey`),
    actOnItem: (projectId: string, jrnSubpointId: string, action: JourneyItemAction) =>
      request<JourneySubpoint>("POST", `/api/v1/projects/${projectId}/journey/items/${jrnSubpointId}`, action),
    continueSection: (projectId: string, jrnSectionId: string) =>
      request<JourneySectionContinueResult>(
        "POST",
        `/api/v1/projects/${projectId}/journey/sections/${jrnSectionId}/continue`
      ),
  },
  workflowRuns: {
    get: (runId: string) => request<WorkflowRun>("GET", `/api/v1/workflow-runs/${runId}`),
  },
  screenplay: {
    listVersions: (projectId: string) =>
      request<ScreenplayVersion[]>("GET", `/api/v1/projects/${projectId}/screenplay-versions`),
    importVersion: (projectId: string, body: ScreenplayVersionImportBody) =>
      request<ScreenplayVersion>("POST", `/api/v1/projects/${projectId}/screenplay-versions`, body),
    getVersion: (projectId: string, versionId: string) =>
      request<ScreenplayVersion>("GET", `/api/v1/projects/${projectId}/screenplay-versions/${versionId}`),
    updateVersion: (projectId: string, versionId: string, body: ScreenplayVersionUpdateBody) =>
      request<ScreenplayVersion>(
        "PATCH",
        `/api/v1/projects/${projectId}/screenplay-versions/${versionId}`,
        body
      ),
    diff: (projectId: string, versionId: string, against: string) =>
      request<ScreenplayDiff>(
        "GET",
        `/api/v1/projects/${projectId}/screenplay-versions/${versionId}/diff?against=${against}`
      ),
    revise: (projectId: string, baseVersionId: string) =>
      request<ScreenplayVersion>(
        "POST",
        `/api/v1/projects/${projectId}/screenplay-versions/${baseVersionId}/revise`
      ),
    submit: (projectId: string, versionId: string, justification: string) =>
      request<ScreenplayVersion>(
        "POST",
        `/api/v1/projects/${projectId}/screenplay-versions/${versionId}/submit`,
        { justification }
      ),
    decide: (projectId: string, versionId: string, body: ScreenplayDecisionBody) =>
      request<ScreenplayDecisionResult>(
        "POST",
        `/api/v1/projects/${projectId}/screenplay-versions/${versionId}/decide`,
        body
      ),
    confirmLegacyLock: (projectId: string, versionId: string) =>
      request<ScreenplayVersion>(
        "POST",
        `/api/v1/projects/${projectId}/screenplay-versions/${versionId}/confirm-legacy-lock`
      ),
    previewImpact: (projectId: string, versionId: string) =>
      request<ImpactPreview>(
        "GET",
        `/api/v1/projects/${projectId}/screenplay-versions/${versionId}/impact-preview`
      ),
    generateSuggestions: (projectId: string, versionId: string, body: ScreenplaySuggestionGenerateBody) =>
      request<ScreenplaySuggestion[]>(
        "POST",
        `/api/v1/projects/${projectId}/screenplay-versions/${versionId}/suggestions/generate`,
        body
      ),
    listSuggestions: (projectId: string, versionId: string) =>
      request<ScreenplaySuggestion[]>(
        "GET",
        `/api/v1/projects/${projectId}/screenplay-versions/${versionId}/suggestions`
      ),
    decideSuggestion: (projectId: string, suggestionId: string, body: ScreenplaySuggestionDecisionBody) =>
      request<ScreenplaySuggestion>(
        "POST",
        `/api/v1/projects/${projectId}/screenplay-suggestions/${suggestionId}/decide`,
        body
      ),
    listImpactAnalyses: (projectId: string) =>
      request<ImpactAnalysis[]>("GET", `/api/v1/projects/${projectId}/impact-analyses`),
  },
};
