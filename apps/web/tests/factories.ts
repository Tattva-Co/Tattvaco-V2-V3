/** Minimal, fully-typed fixture builders for the journey/project API shapes, so
 * component tests can construct just the fields they care about without re-typing every
 * required field from the generated schema each time. */
import type { Project, JourneyGroup, JourneySection, JourneySubpoint } from "../src/api/client";

export function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: "prj-1",
    organization_id: "org-1",
    title: "The Iron Crown",
    logline: "A test project.",
    genre: "Drama",
    status: "active",
    production_mode: "fully_ai",
    current_version: 1,
    created_by: "user-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeSubpoint(overrides: Partial<JourneySubpoint> = {}): JourneySubpoint {
  return {
    id: "JRN-01.1.1",
    key: "prepare",
    title: "Review and prepare",
    kind: "work",
    description: "Confirm the relevant source material.",
    status: "not_started",
    not_applicable_reason: null,
    evidence_refs: [],
    notes: null,
    ...overrides,
  };
}

export function makeGroup(overrides: Partial<JourneyGroup> = {}): JourneyGroup {
  return {
    id: "JRN-01.1",
    title: "Project identity",
    purpose: "Establish the project's creative identity.",
    completion_rule: "All subpoints complete",
    required: true,
    na_policy: "never",
    release: "v1",
    status: "not_started",
    applies: true,
    applicability_reason: null,
    act_capability: "project.edit",
    approval_capability: null,
    can_act: true,
    can_approve: false,
    studio_tools: [],
    requirements: [],
    subpoints: [
      makeSubpoint(),
      makeSubpoint({ id: "JRN-01.1.2", key: "validate", kind: "review_gate", title: "Validate and approve" }),
    ],
    system_managed: false,
    ...overrides,
  };
}

export function makeSection(overrides: Partial<JourneySection> = {}): JourneySection {
  return {
    id: "JRN-01",
    title: "Project Workspace & Setup",
    release_label: "V1 foundation",
    status: "not_started",
    can_continue: false,
    groups: [makeGroup()],
    ...overrides,
  };
}
