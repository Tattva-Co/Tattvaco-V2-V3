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

async function request<T>(method: string, path: string, body?: object): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

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

export const api = {
  auth: {
    devLogin: (email: string, fullName?: string) =>
      request<DevLoginResponse>("POST", "/api/v1/auth/dev-login", { email, full_name: fullName }),
  },
  projects: {
    list: () => request<Project[]>("GET", "/api/v1/projects"),
    get: (id: string) => request<Project>("GET", `/api/v1/projects/${id}`),
    create: (body: ProjectCreateBody) => request<Project>("POST", "/api/v1/projects", body),
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
};
