# Tattva AI Film Director — Screen Inventory and Behaviour

**Doc ID:** TFD-PRD-SCR-001 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval

**Inputs:**
- `INFORMATION_ARCHITECTURE.md`, the canonical list of 60 screens and 1 deferred screen
- `PRD_v1.0.md`, requirement IDs
- Master Execution Prompt §25, which defines the per-screen fields
- IA v1.0 §16 (state UX) and Wireframe Spec v1.0 §6 (dialogs and state rules)
- `docs/audit/03` (route inventory) and `docs/audit/04` (current views)

**Scope:** every screen in the IA is specified with the 15 fields required by Master §25. Shared behaviour is defined once in §1 and referenced as `STD-*`, so that per-screen entries contain only screen-specific behaviour.

---

## 1. Shared conventions

### 1.1 API naming

- All routes sit under `/api/v1`.
- **(exists)** marks a route that is in the code today (`apps/api/routers/*.py`; inventory in `docs/audit/03` §2).
- **(target)** marks a route that follows the convention below. `docs/architecture/API_AND_EVENT_CONTRACTS.md` owns the final names, payloads and error codes.

**Target conventions:**
- Resources are project-scoped plurals: `/projects/{pid}/<resources>[/{id}]`.
- State transitions are `POST …/{id}/<verb>`, for example `/submit`, `/revoke`, `/export`.
- AI workflows start via `POST /projects/{pid}/workflows/<name>` and return **202 + `run_id`**. Status is read from `GET /workflow-runs/{run_id}` (exists).
- Every list route is cursor-paginated (TFD-OPS-010).
- Every create or cost-bearing POST accepts `Idempotency-Key` (TFD-OPS-004).
- Decisions use the existing `POST /approvals/{id}/decide` (exists). The request body is extended with `approval_level` and `target_version`.

**Workflow IDs:**

| ID | Workflow | Status |
|---|---|---|
| WF-01 | Script Intelligence | Exists, legacy G-01 |
| WF-02 | Historical Research | Exists, legacy G-02 |
| WF-03 | Storyboard | Exists, legacy G-03 |
| WF-04 | Film Bible | WIP, legacy G-04 |
| WF-05 | Character/Asset | Target |
| WF-06 | Shot Planning, including cinematography recommendations | Target |
| WF-07 | Continuity | Target |
| WF-08 | AI Director Review | Target |
| WF-09 | Prompt Compilation | Target |
| WF-10 | External Handoff | Target |
| WF-11 | Output Inspection | Target |

This document additionally **proposes WF-15 Screenplay Suggestions, WF-12 Capture Plan Generation and WF-13 Footage Analysis**. Final numbering belongs to `AI_SYSTEM_ARCHITECTURE.md`.

### 1.2 Standard states

| Code | Behaviour |
|---|---|
| **STD-LOAD** | Skeleton layout. Long work shows the **real** stage name from `workflow_runs`/jobs and never a fake percentage. The user can navigate away; the task continues in S-OPS-01 |
| **STD-EMPTY** | Explains what the screen holds, why it is empty, and the single most useful next action. It never forces a template, format or classification |
| **STD-ERR** | Uses the pattern *what happened → what is affected → what remains safe → next action* (IA v1.0 §16). The error is mapped from the API error class: 401 re-authenticate and restore; 403 action-specific block with request-access route; 404 "not found or no access" (no existence oracle); 409 version/lock conflict, which opens a compare dialog; 413/415 file-specific; 422 field-level messages. 5xx shows the correlation ID |
| **STD-RECOVER** | Unsaved edits are kept locally until the save is confirmed. Retries reuse the same `Idempotency-Key`. Failed workflow stages can be retried from the failure point (TFD-OPS-003). Stale objects show their base version and the current version, with Compare / Refresh / Rerun actions |
| **STD-APPROVAL** | Candidate, approved and canonical states are visually distinct and never use colour alone. Each approval shows the exact target version, `approval_level`, required capability and approver. An approval action only appears if the user holds the capability; otherwise "Request review" is shown. AI never presents an approve control on its own output |
| **STD-MOCK** | When the generator is `mock` or `deterministic`, a persistent label is shown on the screen and on every candidate (TFD-AID-006) |
| **STD-CONSENT** | When a selection involves a performer, a consent chip shows each gated purpose's status (`active`, `missing`, `expired`, `revoked`). Gated actions are disabled and the disabled state explains which purpose is missing (TFD-CNS-003) |

### 1.3 Permissions vocabulary

Capabilities are those listed in PRD §12, with the final matrix set by **OPEN — DEC-027**.

- `project.read` is implied by project membership.
- A screen is readable with `project.read` unless stated otherwise.
- Only write capabilities are listed per screen.

---

## 2. Global screens

### S-GLB-01 Home / Project Portfolio
**Release:** FD-V1 · **Aliases:** G-01, G-02, UX-FD-01 · **Current:** `apps/ui/app.py` sidebar selector (`list_projects`, `get_project`) · **Reqs:** TFD-PRJ-002, TFD-IAM-003

| Field | Specification |
|---|---|
| Purpose | Find, resume and search the projects the user can access |
| Primary users | All roles |
| Inputs | Search text; filters (format, mode, status, archived) |
| Outputs | Project cards showing title, format, mode chip, canonical screenplay version, pending approvals for the user, and running or failed tasks |
| Primary actions | Open project; New project (→ S-GLB-02) |
| Secondary actions | Archive / unarchive (`project.manage`); pin |
| API | `GET /projects` (exists; target adds membership filter, pagination and query params); `POST /projects/{pid}/archive` (target) |
| Entities | `projects`, `project_memberships`, `approval_requests`, `workflow_runs` |
| Permissions | List shows member projects only; archive needs `project.manage` |
| Loading | STD-LOAD (card skeletons) |
| Empty | "No projects yet". Two entry points: start from an idea, or start from existing material. Neither forces a format choice |
| Error | STD-ERR |
| Recovery | Last-opened project is restored after re-authentication |
| Approval | Badge showing the count of approvals awaiting this user (links to S-APR-01) |

**Acceptance criteria**
1. A user with no membership in project X never sees X in the list or in search results. A direct link to X returns 404.
2. Archived projects are hidden by default and shown under the "Archived" filter.
3. Cards never show completion percentages.

### S-GLB-02 New Project
**Release:** FD-V1 · **Aliases:** G-03, UX-FD-01 · **Current:** `app.py` "New Film Project" form (title, logline, 4 fixed genres → `create_project`) · **Reqs:** TFD-PRJ-001, TFD-PRJ-003, TFD-FMT-001, TFD-FMT-002, TFD-FMT-003

| Field | Specification |
|---|---|
| Purpose | Create a project with format template, production mode, quality profile, scale, team and delivery profile (Stage 1) |
| Primary users | Producer, Director, Project owner |
| Inputs | Title (required); logline; genre (free text with suggestions); format template (13 options or "decide later"); production mode (`fully_ai` / `hybrid_live_action` / `mixed`, required, `mixed` preselected); visual quality profile; scale; output profiles; initial members; optional files (handed to S-AST-01) |
| Outputs | New project at version 1, with the creator as `project_owner` |
| Primary actions | Create |
| Secondary actions | Add files now; invite members |
| API | `POST /projects` (exists; body extended, with old fields still accepted); `GET /project-templates` (target); `POST /projects/{pid}/output-profiles` (target); `POST /projects/{pid}/members` (target) |
| Entities | `projects` (+ `format_template_id`, `production_mode`, `quality_profile`, `scale`), `output_profiles`, `project_memberships` |
| Permissions | `org.project.create` |
| Loading | Template list skeleton |
| Empty | n/a |
| Error | 422 field errors inline; idempotent retry |
| Recovery | Form draft preserved on error or refresh |
| Approval | None. Creation is not an approval-gated action |

**Acceptance criteria**
1. A project can be created with only a title and a mode. The other fields show "decide later", and the project header shows which of them must be set before packaging.
2. Choosing "OTT series" or "Episodic historical series" creates the episode structure and an episode selector.
3. Double-submitting with the same `Idempotency-Key` creates one project.

### S-OPS-01 Task Centre
**Release:** FD-V1 (FD-V2 adds generation jobs) · **Aliases:** G-04, UX-FD-25 · **Current:** none. The UI blocks on `sync_execution=True` (`docs/audit/04`) · **Reqs:** TFD-OPS-001, TFD-OPS-002, TFD-OPS-005, TFD-GEN-001, TFD-GEN-003

| Field | Specification |
|---|---|
| Purpose | Monitor and recover long-running work across the user's projects |
| Primary users | All roles; Production operator |
| Inputs | Filters: project, state, type (workflow / generation job / import / export) |
| Outputs | Task rows showing type, project, target object, real stage, state (11 task states), age and error class |
| Primary actions | Open result; Retry from failed stage; Cancel |
| Secondary actions | Open the unknown-outcome reconcile drawer (FD-V2); view logs (correlation ID) |
| API | `GET /workflow-runs/{id}` (exists); `GET /tasks` (target, aggregates `workflow_runs`, `generation_jobs`, `import_jobs`, `exports`); `POST /workflow-runs/{id}/retry` and `/cancel` (target); `POST /generation-jobs/{id}/reconcile` (target, V2) |
| Entities | `workflow_runs`, `outbox_tasks`, `generation_jobs`, `generation_attempts`, `import_jobs` |
| Permissions | Rows filtered to member projects; retry and cancel need the capability that started the task |
| Loading | STD-LOAD; polling with backoff (a push channel depends on DEC-009) |
| Empty | "No background work". Explains that long tasks appear here |
| Error | Per-row error class and correlation ID; a dead-lettered task shows "needs attention" |
| Recovery | Retry resumes from the checkpoint, not from START (TFD-OPS-003). For an `unknown_outcome` job, retry is disabled until it is reconciled |
| Approval | Rows in `awaiting_approval` link to S-APR-02 |

**Acceptance criteria**
1. Starting any WF from any screen returns immediately, and the task appears here in `queued` within one poll interval.
2. Killing a worker mid-task leads to lease expiry, re-claim, and resumption from the checkpoint without duplicate candidates.
3. An `unknown_outcome` job cannot be retried until it is reconciled.

### S-APR-01 Approvals Inbox
**Release:** FD-V1 · **Aliases:** G-05, UX-FD-24 · **Current:** `apps/ui/views/review.py` (unified tray for 4 scopes; approve-selected / reject-all via `get_candidates`, `decide_approval`) · **Reqs:** TFD-APR-001, TFD-APR-005, TFD-APR-006

| Field | Specification |
|---|---|
| Purpose | One queue of approvals the user can decide, across projects or filtered to the current project |
| Primary users | Management approver, Director, Leads, Producer, Consent manager |
| Inputs | Filters: project, `approval_level` (creative / management / cost / consent), target type, age |
| Outputs | Rows showing target, version, level, requester, consequence summary, and stale flag |
| Primary actions | Open detail (→ S-APR-02) |
| Secondary actions | Reassign (`project.manage_members`); bulk-open |
| API | `GET /approvals?scope=mine` (target); `GET /projects/{pid}/candidates` (exists, used for the WF-01…04 scopes) |
| Entities | `approval_requests` (generalised) |
| Permissions | Only rows whose `required_capability` the user holds |
| Loading | STD-LOAD |
| Empty | "Nothing awaiting your decision" |
| Error | STD-ERR |
| Recovery | A stale row (target version moved) is labelled and routed to re-review |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. A user without `screenplay.approve_lock` never sees management-level rows.
2. All four existing scopes (`script_intelligence_candidates`, `historical_research_candidates`, `storyboard_candidates`, `film_bible_rules`) appear with no data migration.
3. An unknown scope never renders a decide action. The API returns 422 (TFD-APR-002).

### S-REG-01 Production Tool Registry
**Release:** FD-V1 (manual targets) → FD-V2 (connected snapshots) · **Aliases:** G-07 (part), UX-FD-21 · **Current:** none. Only `higgsfield_*` config fields in `packages/core/config.py` · **Reqs:** TFD-INT-003, TFD-INT-004, TFD-INT-006, TFD-PKG-006

| Field | Specification |
|---|---|
| Purpose | Show which tools and models exist, how each can be executed (manual / API / MCP), and their verification status |
| Primary users | Production operator, Director, Org admin |
| Inputs | Filters: task category (image, video, performance transfer, avatar, mocap, measurement, voice, lip-sync), execution mode, verification status |
| Outputs | Provider cards and capability snapshots with all Master §12.3 fields, verification date and source, the `automation_permitted` flag, and a manual-alternative note |
| Primary actions | View snapshot; compare tools for a task |
| Secondary actions | Propose a registry entry (`registry.propose`); mark re-verification due |
| API | `GET /providers`, `GET /providers/{id}/snapshots` (target) |
| Entities | `providers`, `provider_capability_snapshots` |
| Permissions | Read: all members; edit entries: `registry.manage` (Product/Eng) |
| Loading | STD-LOAD |
| Empty | "No tools registered". In FD-V1 the seed holds manual-target entries, all marked **UNVERIFIED** |
| Error | STD-ERR |
| Recovery | Snapshot history is preserved; the previous snapshot can be viewed |
| Approval | A new snapshot or status change needs `registry.approve` sign-off. UNVERIFIED entries cannot be enabled as connected |

**Acceptance criteria**
1. Every entry shows a verification status and date. UNVERIFIED entries show "manual only".
2. Midjourney shows `automation_permitted=false` and only offers manual execution (TFD-INT-006).
3. No screen text describes a tool as "connected" or "integrated" unless a connection exists and has passed onboarding.

### S-REG-02 Provider Connections
**Release:** FD-V2 · **Aliases:** G-07 (part), UX-FD-21 · **Current:** none · **Reqs:** TFD-INT-005, TFD-INT-007, TFD-INT-009, TFD-INT-010, TFD-CNS-008

| Field | Specification |
|---|---|
| Purpose | Connect, test, scope and disconnect org-level provider accounts, and record the onboarding gate |
| Primary users | Org admin, Production operator, Legal (terms review) |
| Inputs | Provider; execution mode (API / MCP); credentials (written directly to the secret store); allowed projects; spend cap |
| Outputs | Connection status (`not_connected`, `testing`, `active`, `auth_expired`, `schema_changed`, `disabled`); last test; discovered tools (MCP); onboarding checklist status |
| Primary actions | Connect; Test; Disconnect |
| Secondary actions | Re-discover schema; view the snapshot diff |
| API | `GET/POST /provider-connections`, `POST /provider-connections/{id}/test`, `/discover`, `/disable` (target) |
| Entities | `provider_connections`, `provider_capability_snapshots`, onboarding record |
| Permissions | `provider.connect` (org admin) plus a Legal sign-off record for the terms gate |
| Loading | Testing shows the real step (auth → discovery → schema validation) |
| Empty | "No connections. Manual execution is available for every tool." |
| Error | Auth failure, schema change and provider down each have distinct messages. Secrets are never echoed |
| Recovery | `schema_changed` blocks actions until a human approves the new snapshot (TFD-INT-010) |
| Approval | Enabling connected mode needs the completed onboarding gate (TFD-INT-005) |

**Acceptance criteria**
1. A credential value is never returned by any API or rendered after it has been saved.
2. A connection cannot reach `active` without a signed onboarding record.
3. A disconnected provider leaves every package exportable manually (TFD-INT-008).

### S-LIB-02 Shared Organisation Library
**Release:** FD-V2 · **Aliases:** G-06 · **Current:** none · **Reqs:** TFD-LIB-003, TFD-DH-009

| Field | Specification |
|---|---|
| Purpose | Reuse approved org-level assets and digital humans across projects |
| Primary users | Digital human lead, Art lead, Producer |
| Inputs | Search; filters (type, owner project, consent scope) |
| Outputs | Assets with owner project, licence/rights and consent scope |
| Primary actions | Request reuse in project X |
| Secondary actions | View lineage |
| API | `GET /org/library`, `POST /org/library/{id}/reuse-requests` (target) |
| Entities | `assets`, `digital_humans`, `avatar_versions`, `performer_consents` |
| Permissions | `library.org.read`; reuse needs `library.reuse` plus a consent check |
| Loading | STD-LOAD |
| Empty | "Nothing shared yet" |
| Error | STD-ERR |
| Recovery | A failed reuse request is retryable idempotently |
| Approval | Reuse of performer-derived items needs `future_project_reuse` consent and the target project owner's approval |

**Acceptance criteria**
1. A digital human whose consent excludes `future_project_reuse` cannot be reused, and the block names that purpose.
2. A reused item keeps its original lineage and records the new project link.

### S-TEAM-01 Organisation Members & Roles
**Release:** FD-V1 · **Aliases:** G-08 · **Current:** none (`users.role` unused) · **Reqs:** TFD-IAM-002, TFD-IAM-004, TFD-IAM-008

| Field | Specification |
|---|---|
| Purpose | Manage org memberships and role templates |
| Primary users | Org admin |
| Inputs | Invite email; role; deactivate |
| Outputs | Member list with org role and project count |
| Primary actions | Invite; change role; deactivate |
| Secondary actions | View the capability matrix (read-only, from DEC-027) |
| API | `GET/POST /org/members`, `PATCH /org/members/{id}`, `GET /role-templates` (target) |
| Entities | `users`, `memberships`, `role_templates`, `capabilities` |
| Permissions | `org.manage_members` |
| Loading | STD-LOAD |
| Empty | Only the admin is listed; invite prompt shown |
| Error | STD-ERR |
| Recovery | Deactivation takes effect on the next request; pending approvals are re-routed (TFD-IAM-008) |
| Approval | Granting `management_approver` or `consent_manager` needs a second org admin's confirmation (recommendation under DEC-027) |

**Acceptance criteria**
1. The org admin role alone does not grant any creative, management or consent capability.
2. A deactivated user's API calls fail with 401/403 on the next request.

---

## 3. Project Workspace, Settings, Team

### S-PRJ-01 Project Overview
**Release:** FD-V1 · **Aliases:** P-01, UX-FD-02 · **Current:** `apps/ui/views/overview.py` (asset/scene/entity counts plus project JSON) · **Reqs:** TFD-PRJ-007

| Field | Specification |
|---|---|
| Purpose | Answer five questions: where am I, what is understood, what is unresolved, what needs me, and what to do next |
| Primary users | Director, Producer |
| Inputs | Project context |
| Outputs | Canonical screenplay version and lock state; mode distribution (shots by effective mode and method); pending approvals; high-severity findings; running and failed tasks; recent changes; next-best action with its reason |
| Primary actions | Follow the next action; open an item |
| Secondary actions | Switch episode |
| API | `GET /projects/{pid}` (exists); `GET /projects/{pid}/summary` (target aggregate); `GET /projects/{pid}/versions`, `/audit-log` (exist) |
| Entities | `projects`, `screenplay_versions`, `shots`, `approval_requests`, `continuity_findings`, `workflow_runs` |
| Permissions | `project.read` |
| Loading | Section-level skeletons; each section loads independently |
| Empty | New project shows "Add your screenplay or material" and the chosen mode and format |
| Error | A failed section shows an inline error; other sections still render |
| Recovery | Per-section retry |
| Approval | Lists approvals awaiting the user, with level |

**Acceptance criteria**
1. No percentage or score is shown that is not derived from stored data.
2. The screenplay version shown equals the single `is_production_canonical` version (or "none locked").
3. The generator-mode banner appears if any mock generator produced data on display (STD-MOCK).

### S-PRJ-02 Project Settings & Governance
**Release:** FD-V1 · **Aliases:** P-36, UX-FD-26 · **Current:** none · **Reqs:** TFD-PRJ-002, TFD-PRJ-003, TFD-PRJ-006, TFD-FMT-002, TFD-FMT-004, TFD-FMT-005, TFD-IAM-006

| Field | Specification |
|---|---|
| Purpose | Manage project metadata, format template, default mode, output profiles, data policy, provider policy and budgets |
| Primary users | Project owner, Producer |
| Inputs | Metadata; template; project mode; output profiles; data policy (allowed provider data classes); budget caps (V2) |
| Outputs | Saved settings; impact preview for mode or template change |
| Primary actions | Save; change mode (opens impact preview first); archive |
| Secondary actions | Export project archive (→ S-PST-01) |
| API | `PATCH /projects/{pid}` (target); `POST /projects/{pid}/impact-analyses` (target, preview mode); `GET/POST /projects/{pid}/output-profiles` (target); `PUT /projects/{pid}/budget` (target, V2) |
| Entities | `projects`, `output_profiles`, `impact_analyses`, project policy JSON |
| Permissions | `project.manage`; budget needs `cost.approve` |
| Loading | STD-LOAD |
| Empty | Unset fields show "decide later" with the consequence (for example, packaging blocked until a delivery profile exists) |
| Error | 409 on a concurrent edit opens the compare dialog |
| Recovery | STD-RECOVER |
| Approval | A mode change with affected approved shots needs Director confirmation and marks those shots `review_required` |

**Acceptance criteria**
1. Changing the project mode from `fully_ai` to `mixed` shows the count of affected sequences, scenes and shots before saving, and changes no approved shot.
2. Settings changes are audited with before and after values.

### S-TEAM-02 Project Members & Roles
**Release:** FD-V1 · **Aliases:** P-36 (members), UX-FD-26 · **Current:** none · **Reqs:** TFD-IAM-003, TFD-IAM-004, TFD-IAM-005

| Field | Specification |
|---|---|
| Purpose | Assign project roles (including management approver and consent manager) |
| Primary users | Project owner |
| Inputs | Member and role template; per-capability grants where allowed |
| Outputs | Member list with effective capabilities |
| Primary actions | Add; change role; remove |
| Secondary actions | View who can approve what |
| API | `GET/POST /projects/{pid}/members`, `PATCH/DELETE /projects/{pid}/members/{uid}` (target) |
| Entities | `project_memberships`, `role_templates`, `capabilities` |
| Permissions | `project.manage_members` |
| Loading | STD-LOAD |
| Empty | Creator only |
| Error | STD-ERR |
| Recovery | Removing the last `management_approver` is blocked with an explanation |
| Approval | As S-TEAM-01 for privileged roles |

**Acceptance criteria**
1. A project must keep at least one `screenplay.approve_lock` holder once a screenplay is locked.
2. A removed member loses access on the next request.

---

## 4. Intake & Assets

### S-AST-01 Intake Inbox
**Release:** FD-V1 · **Aliases:** P-03, UX-FD-03, G-03 (files) · **Current:** `apps/ui/views/assets.py` upload (.fountain/.txt/.pdf → `upload_asset`); `POST /projects/{pid}/assets/upload` buffers the whole file (`routers/assets.py:27`) · **Reqs:** TFD-AST-001, TFD-AST-002, TFD-AST-003, TFD-AST-005, TFD-AST-006, TFD-CNS-003

| Field | Specification |
|---|---|
| Purpose | Bring any material in and see each file's outcome |
| Primary users | All contributors |
| Inputs | Multiple files; category hint per file; rights declaration; for performer references, the performer link |
| Outputs | Per-file receipt and state: `uploading → received → scanning → accepted / quarantined / rejected → processing → processed / partially_processed / failed` |
| Primary actions | Upload; set category |
| Secondary actions | Retry a failed file; remove a not-yet-accepted file; route to the next step (for example, "Import as screenplay" → S-SCR-01) |
| API | `POST /projects/{pid}/assets/upload` (exists, kept for compatibility); `POST /projects/{pid}/assets/uploads` (target, presigned init) + `/uploads/{id}/complete`; `PATCH /projects/{pid}/assets/{aid}` (classification) |
| Entities | `assets`, `asset_derivatives`, `import_jobs` |
| Permissions | `asset.upload`; performer-reference categories also need an active `reference_storage` consent |
| Loading | Per-file progress from real bytes sent; processing shows the real stage |
| Empty | Dropzone listing the accepted categories and limits |
| Error | Per-file errors only: 413 size, 415 signature mismatch, quarantine reason. The batch continues |
| Recovery | Resumable uploads where the storage adapter supports them; retry per file |
| Approval | Performer-reference upload without consent is blocked with STD-CONSENT. No other approvals |

**Acceptance criteria**
1. Uploading 10 files where one has a signature mismatch yields 9 accepted and 1 rejected, each with its own receipt (TFD-AST-005).
2. A 2 GB video upload does not increase API process memory by more than the streaming buffer (TFD-AST-001).
3. A PDF screenplay yields a text derivative from its text layer and is never decoded as UTF-8 bytes (TFD-AST-006).

### S-AST-02 Asset Library (inputs)
**Release:** FD-V1 · **Aliases:** P-04, UX-FD-04 · **Current:** `assets.py` list (filename + checksum via `GET /projects/{pid}/assets`) · **Reqs:** TFD-AST-003, TFD-AST-004, TFD-AST-008, TFD-AST-010, TFD-IAM-007

| Field | Specification |
|---|---|
| Purpose | Find, filter and organise all project inputs and derivatives |
| Primary users | All |
| Inputs | Search; filters (category, state, source, linked entity, rights) |
| Outputs | Grid or list with checksum, provenance, linked entities and duplicate candidates |
| Primary actions | Open inspector |
| Secondary actions | Re-classify; link to entity; bulk tag; download (signed URL) |
| API | `GET /projects/{pid}/assets` (exists; target adds filters and pagination); `GET /projects/{pid}/assets/{aid}/download-url` (target) |
| Entities | `assets`, `asset_lineage` |
| Permissions | Sensitive categories are redacted without `identity.view_sensitive` |
| Loading | STD-LOAD |
| Empty | Link to S-AST-01 |
| Error | STD-ERR |
| Recovery | n/a |
| Approval | Classification changes are audited and are not approval-gated |

**Acceptance criteria**
1. Performer face, body and voice references appear as "restricted" placeholders to users without `identity.view_sensitive`, and their download URLs return 404.
2. Download links expire, and a link reused after expiry fails.

### S-AST-03 Asset Inspector
**Release:** FD-V1 → FD-V2 (media proxies, frame scrubbing) · **Aliases:** P-05, UX-FD-05, UX-FD-15 · **Current:** none · **Reqs:** TFD-AST-004, TFD-AST-006, TFD-AST-007, TFD-AST-009

| Field | Specification |
|---|---|
| Purpose | Inspect one asset: preview, extracted content, metadata, derivatives, lineage, findings. Reference videos get a timecoded observation mode |
| Primary users | All |
| Inputs | Asset ID; for reference video, the purpose tag |
| Outputs | Preview; text or frames; metadata; derivative list; lineage graph; observations |
| Primary actions | Correct classification; tag reference purpose; link to entity |
| Secondary actions | Reprocess a derivative; open source locator |
| API | `GET /projects/{pid}/assets/{aid}`, `/derivatives`, `/lineage` (target); `POST /projects/{pid}/workflows/reference-analysis` (target, P1) |
| Entities | `assets`, `asset_derivatives`, `asset_lineage` |
| Permissions | As S-AST-02 |
| Loading | Preview loads the proxy, not the original |
| Empty | "No derivatives yet", showing processing state |
| Error | Unsupported preview shows a metadata-only view |
| Recovery | Reprocess a single failed derivative |
| Approval | Observation candidates are approved via S-APR-02 |

**Acceptance criteria**
1. The original is never modified. Reprocessing creates new derivative rows.
2. The lineage graph shows the original → derivatives → downstream artifacts that reference them.

---

## 5. Story Brain

### S-BRN-01 Story Brain
**Release:** FD-V1 · **Aliases:** P-02, UX-FD-06 · **Current:** none · **Reqs:** TFD-STY-004, TFD-CTX-004

| Field | Specification |
|---|---|
| Purpose | Show what Tattva knows, does not know, and is unsure about, so users can correct it |
| Primary users | Director, Story lead, Researcher |
| Inputs | Filters by entity and epistemic state |
| Outputs | Facts grouped as known, unknown, ambiguous, assumed, conflicting, blocked and resolved, each with evidence and source locator |
| Primary actions | Correct (creates a candidate); resolve; ask a question (→ S-RES-02) |
| Secondary actions | View the context packages that used this fact |
| API | `GET /projects/{pid}/story-brain` (target); `POST /projects/{pid}/story-brain/corrections` (target) |
| Entities | Story Brain facts (owned by `DATABASE_DESIGN_AND_ERD.md`), `context_packages` |
| Permissions | Corrections need `story.edit` |
| Loading | STD-LOAD |
| Empty | "Nothing analysed yet" |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | Corrections to canonical facts go through approval |

**Acceptance criteria**
1. An unknown is never displayed as known.
2. Every fact links to at least one source locator, or is labelled `user_assertion`.

### S-BRN-02 Narrative Timeline
**Release:** FD-V1 (P1) · **Aliases:** P-18 · **Current:** none · **Reqs:** TFD-STY-005, TFD-CHR-007

| Field | Specification |
|---|---|
| Purpose | Story chronology (flashbacks, ages, states), distinct from the historical timeline |
| Primary users | Story lead, Director |
| Inputs | Scene order and story-time annotations |
| Outputs | Lanes per character showing age and state; scene order vs story order |
| Primary actions | Set story time; link to historical event |
| Secondary actions | Toggle the historical overlay (from S-RES-04) |
| API | `GET /projects/{pid}/story-timeline`; `PATCH /projects/{pid}/scenes/{sid}` (story_time) (target) |
| Entities | `timeline_events` (kind=story), `scenes`, `character_states` |
| Permissions | `story.edit` |
| Loading | STD-LOAD |
| Empty | "No story-time annotations" |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | Changes are candidates until approved |

**Acceptance criteria**
1. The historical and story timelines can be shown together but are stored as different kinds.
2. A list or table alternative exists for accessibility.

---

## 6. Screenplay Studio

### S-SCR-01 Screenplay Versions & Lock
**Release:** FD-V1 · **Aliases:** new · **Current:** none. The script is an `assets` row (V1-05 NOT_IMPL) · **Reqs:** TFD-SCR-001, TFD-SCR-002, TFD-SCR-003, TFD-SCR-007, TFD-SCR-008, TFD-SCR-011, TFD-IAM-005

| Field | Specification |
|---|---|
| Purpose | See every screenplay version and which one is production canonical; submit for lock; management decides |
| Primary users | Management approver, Director, Story lead |
| Inputs | Source asset (from S-AST-01) to import; episode (episodic formats) |
| Outputs | Version list showing number, status (`draft`, `in_review`, `approved_locked`, `superseded`, `rejected`), canonical flag, derived-from, approver and timestamps |
| Primary actions | Import screenplay (creates a draft); Submit for lock; **Approve and lock** (management); Reject |
| Secondary actions | Compare two versions (→ S-SCR-03 diff view); view impact (→ S-CON-03) |
| API | `GET/POST /projects/{pid}/screenplay-versions` (target); `POST /projects/{pid}/screenplay-versions/{vid}/submit` (target); `POST /approvals/{id}/decide` (exists; `approval_level=management`) |
| Entities | `screenplay_versions`, `screenplay_changes`, `approval_requests`, `assets` |
| Permissions | Import and submit: `screenplay.propose_revision`; approve/lock: `screenplay.approve_lock` |
| Loading | STD-LOAD; import parse is shown as a task |
| Empty | "No screenplay yet". Explains that the screenplay is the narrative authority once locked. Documentary template: "optional" |
| Error | 409 `screenplay_locked` on any edit attempt against a locked version |
| Recovery | Parse failure keeps the asset and allows reprocessing |
| Approval | Management-level approval with exact version; the canonical flag moves atomically |

**Acceptance criteria**
1. Two concurrent lock approvals for different versions result in exactly one canonical version (TFD-SCR-002).
2. A director without `screenplay.approve_lock` sees "Submit for management review", never "Approve".
3. Backfilled legacy script assets appear as v1 in `draft` unless an owner confirmed them as locked.

### S-SCR-02 Script & Scene Breakdown
**Release:** FD-V1 · **Aliases:** P-06, UX-FD-10 · **Current:** `apps/ui/views/script_intelligence.py` (runs WF-01 synchronously, raw JSON output) · **Reqs:** TFD-SCR-004, TFD-SCR-009, TFD-STY-001, TFD-STY-002, TFD-STY-003, TFD-STY-007

| Field | Specification |
|---|---|
| Purpose | Read the locked screenplay with extracted scenes, verbatim dialogue, characters, locations and locators |
| Primary users | Director, Story lead, all crew (read) |
| Inputs | Screenplay version (defaults to canonical) |
| Outputs | Script viewer with scene list; dialogue segments; entity mentions; extraction candidates awaiting approval |
| Primary actions | Run analysis (WF-01, async); open a candidate batch for approval |
| Secondary actions | Jump to a character, location or scene planner; flag an extraction error |
| API | `POST /projects/{pid}/workflows/script-intelligence` (exists; target body adds `screenplay_version_id`, async default); `GET /projects/{pid}/scenes`, `/entities` (exist); `GET /projects/{pid}/dialogue-segments` (target) |
| Entities | `screenplay_versions`, `scenes`, `scene_candidates`, `entities`, `entity_candidates`, `dialogue_segments`, `characters`, `locations` |
| Permissions | Run: `story.analyse`; approval via S-APR-02 (`canon.approve.story`) |
| Loading | Task status; the viewer remains usable |
| Empty | "No analysis for this version" + Run |
| Error | Parse errors per scene, with locator |
| Recovery | Re-run creates new candidates; approved scenes are superseded only through approval |
| Approval | Candidate batches use the existing partial approval |

**Acceptance criteria**
1. No control on this screen edits screenplay text.
2. Dialogue shown equals the source text byte-for-byte on the golden set (TFD-STY-002).
3. Results render as structured scenes and dialogue, not raw JSON (`docs/audit/04` §4.3).

### S-SCR-03 Revision Workspace
**Release:** FD-V1 · **Aliases:** new · **Current:** none · **Reqs:** TFD-SCR-006, TFD-SCR-007, TFD-SCR-010, TFD-SCR-012, TFD-APR-007

| Field | Specification |
|---|---|
| Purpose | The director prepares a revision: edit, compare, justify, submit; management reviews with impact |
| Primary users | Director, Story lead (author); Management approver (reviewer) |
| Inputs | Base = canonical version; revised file upload **or** scene-level structured edits; suggestions pulled from S-SCR-04; per-change justification |
| Outputs | Change set (`screenplay_changes`: scene added, removed or modified; dialogue changed; action changed) with diff; impact preview |
| Primary actions | Create revision; edit; Submit for management review; (management) Approve / Reject / Request changes |
| Secondary actions | Discard draft; compare with any other version |
| API | `POST /projects/{pid}/screenplay-versions/{vid}/revisions` (target); `GET /projects/{pid}/screenplay-versions/{vid}/diff?against={vid2}` (target); `PATCH /projects/{pid}/screenplay-versions/{vid}` (draft only); `POST …/{vid}/submit`; `POST /projects/{pid}/impact-analyses` (target) |
| Entities | `screenplay_versions`, `screenplay_changes`, `screenplay_suggestions`, `impact_analyses`, `approval_requests` |
| Permissions | Author: `screenplay.propose_revision`; review: `screenplay.approve_lock` |
| Loading | Diff and impact are computed as tasks |
| Empty | "No open revision". Create from the canonical version |
| Error | Base version superseded while drafting → 409 → rebase dialog |
| Recovery | The draft auto-saves as a draft version; nothing touches the canonical version |
| Approval | Management approval of the exact draft version. If DEC-027 configures a chain, creative sign-off comes first (TFD-APR-007) |

**Acceptance criteria**
1. Submitting without a justification on every change set is refused (422).
2. Approval creates a new `approved_locked` version, supersedes the old one, and produces an impact analysis listing affected scenes, characters, sequences, shots, assets and packages, all marked `review_required` (TFD-SCR-010).
3. No approved shot or package changes content as a result of the approval.

*Streamlit limitation: a rich redline editor is a P2 item gated on DEC-009. FD-V1 uses side-by-side scene diff plus file re-import.*

### S-SCR-04 AI Suggestions Workspace
**Release:** FD-V1 · **Aliases:** new · **Current:** none · **Reqs:** TFD-SCR-005

| Field | Specification |
|---|---|
| Purpose | Hold AI creative suggestions apart from the screenplay |
| Primary users | Director, Story lead |
| Inputs | Scope (scene range, character); suggestion kinds (7) |
| Outputs | Suggestions anchored to version, scene or line, with rationale and generator mode |
| Primary actions | Generate suggestions (WF-15, async); accept-for-revision; reject; defer |
| Secondary actions | Open in S-SCR-03 |
| API | `POST /projects/{pid}/workflows/screenplay-suggestions` (target, WF-15); `GET /projects/{pid}/screenplay-suggestions` (target); `POST /projects/{pid}/screenplay-suggestions/{sid}/disposition` (target) |
| Entities | `screenplay_suggestions`, `context_packages` |
| Permissions | Generate: `suggestion.request`; dispose: `suggestion.decide` |
| Loading | Task status |
| Empty | "No suggestions. The screenplay is unaffected by this workspace." |
| Error | STD-ERR; invalid model output is rejected and recorded (TFD-AID-003) |
| Recovery | Re-generation adds suggestions; earlier ones are kept |
| Approval | Disposition is recorded but does not approve anything into the screenplay. Only S-SCR-03 + management can do that |

**Acceptance criteria**
1. Accepting a suggestion leaves every `screenplay_versions` row unchanged.
2. Rejected and deferred suggestions remain listed under a filter, with the actor and reason.

---

## 7. Historical Research Studio

### S-RES-01 Historical Brief
**Release:** FD-V1 (P1) · **Aliases:** P-09 · **Current:** none · **Reqs:** TFD-RES-007

| Field | Specification |
|---|---|
| Purpose | Resolve the target period, region, polity, event and fidelity stance |
| Primary users | Researcher, Director |
| Inputs | Date range (original expression + normalised + precision), region, polity, event, fidelity stance (documentary / interpretive / dramatised) |
| Outputs | A versioned brief |
| Primary actions | Save candidate; submit for approval |
| Secondary actions | Generate research questions (→ S-RES-02) |
| API | `GET/PUT /projects/{pid}/research/brief` (target) |
| Entities | Historical brief (artifact), `timeline_events` |
| Permissions | `research.edit`; approve: `canon.approve.research` |
| Loading | STD-LOAD |
| Empty | "Period not set". Choosing a non-historical template hides the prompt but keeps the screen reachable |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. Ambiguous input (for example, "Kalinga era") is stored with precision `approximate` and is never silently normalised to a single year.

### S-RES-02 Investigation Board
**Release:** FD-V1 · **Aliases:** P-10, UX-FD-07 · **Current:** `historical_research.py` tabs Investigate, Questions, Claims, Conflicts; WF-02 investigator is MOCKED (`investigator.py`) · **Reqs:** TFD-RES-001, TFD-RES-003, TFD-RES-004, TFD-RES-005, TFD-RES-009, TFD-RES-010

| Field | Specification |
|---|---|
| Purpose | Run investigations; review typed claims and conflicts |
| Primary users | Researcher |
| Inputs | Questions; investigate trigger; filters by claim class |
| Outputs | Questions with status; claim cards (class, sources, confidence); conflict threads |
| Primary actions | Add question (as a candidate, or role-gated direct with audit); Investigate (WF-02, async); approve claim batch |
| Secondary actions | Mark conflict resolved or dismissed with rationale; flag anachronism |
| API | `GET/POST /projects/{pid}/research/questions` (exists; target routes POST through approval); `GET /research/claims`, `/research/conflicts` (exist); `POST /projects/{pid}/workflows/historical-research` (exists; async target) |
| Entities | `research_questions`, `research_claims`, `research_conflicts`, `research_*_candidates` |
| Permissions | `research.edit`; approve: `canon.approve.research` |
| Loading | Task status |
| Empty | "No questions yet" |
| Error | STD-ERR |
| Recovery | Re-investigate keeps earlier candidates and decisions |
| Approval | Partial approval of claim candidates (existing) |

**Acceptance criteria**
1. A claim without at least one source cannot be approved as `historical_fact` (TFD-RES-004).
2. Every claim produced by the current investigator shows the `mock` label (STD-MOCK).
3. A question created by manual POST appears as a candidate (or audited direct canon with a version bump), never as an unaudited canonical row (TFD-RES-005).

### S-RES-03 Source & Evidence Inspector
**Release:** FD-V1 · **Aliases:** P-11 · **Current:** `historical_research.py` Sources tab; `POST /research/sources` writes canon directly and its `asset_id` is not tenant-validated (SEC-04/06) · **Reqs:** TFD-RES-002, TFD-RES-005, TFD-IAM-009

| Field | Specification |
|---|---|
| Purpose | Register and inspect sources with tier, locator, excerpt, retrieval date and independence |
| Primary users | Researcher |
| Inputs | Source metadata; linked asset; excerpts with locators |
| Outputs | Source card; claims citing it |
| Primary actions | Register source; add excerpt |
| Secondary actions | Mark inaccessible; change tier (audited) |
| API | `GET/POST /projects/{pid}/research/sources` (exists; target validates `asset_id` is in the same project, routes through approval) |
| Entities | `research_sources`, `assets`, `research_claims` |
| Permissions | `research.edit` |
| Loading | STD-LOAD |
| Empty | "No sources" |
| Error | Referencing an asset from another project → 404 |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. Registering a source with another tenant's `asset_id` fails with 404 (TFD-IAM-009).

### S-RES-04 Historical Timeline
**Release:** FD-V1 · **Aliases:** P-12, UX-FD-08 · **Current:** none · **Reqs:** TFD-RES-006

| Field | Specification |
|---|---|
| Purpose | Real-world chronology with uncertain dates, linked to claims and scenes |
| Primary users | Researcher, Director |
| Inputs | Events (original date expression, normalised range, precision, calendar, linked claims) |
| Outputs | Timeline with ranges and contested forks; table alternative |
| Primary actions | Add event (candidate); link to scene |
| Secondary actions | Overlay the story timeline |
| API | `GET/POST /projects/{pid}/research/timeline-events` (target) |
| Entities | `timeline_events` (kind=historical), `research_claims`, `scenes` |
| Permissions | `research.edit` |
| Loading | STD-LOAD |
| Empty | "No events" |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. A contested date is shown as a range or fork, never as a single point.
2. Every event links to at least one claim, or is labelled `user_assertion`.

### S-RES-05 Temporal Visual Profile
**Release:** FD-V1 (P1) · **Aliases:** UX-FD-09 · **Current:** none · **Reqs:** TFD-RES-008, TFD-RES-009

| Field | Specification |
|---|---|
| Purpose | What clothing, grooming, weapons, architecture and materials looked like in this period and region, with evidence |
| Primary users | Art lead, Researcher |
| Inputs | Category; period |
| Outputs | Attributes with claims, uncertainty and reference images |
| Primary actions | Create a costume, prop or environment spec from an attribute (→ S-CST / S-ENV) |
| Secondary actions | Flag gap |
| API | `GET /projects/{pid}/research/visual-profiles` (target) |
| Entities | Visual profile artifact, `research_claims` |
| Permissions | `research.edit` |
| Loading | STD-LOAD |
| Empty | "Set a historical brief first" |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. Every attribute shows claim class and source count; unsupported attributes show `unverified`.

---

## 8. Film Bible & Visual Direction

### S-BIB-01 Film Bible Overview
**Release:** FD-V1 · **Aliases:** P-13 · **Current:** `apps/ui/views/film_bible.py` (rules, synthesis, scenes, entities, versions); backend BROKEN (G04-B) · **Reqs:** TFD-CIN-010, TFD-CIN-012, TFD-VER-005

| Field | Specification |
|---|---|
| Purpose | One view of the approved creative world: Film Bible sections, versions and gaps |
| Primary users | Director, Art lead |
| Inputs | — |
| Outputs | Sections (visual rules, characters, costume, props, environments, cinematography) with approval status and version; explicit "not started" sections |
| Primary actions | Open section |
| Secondary actions | Export bible (→ S-PST-01) |
| API | `GET /projects/{pid}/film-bible/rules` (exists); `GET /projects/{pid}/film-bible/summary` (target) |
| Entities | `film_bible_rules`, `characters`, `costumes`, `props`, `locations`, `cinematography_profiles` |
| Permissions | `project.read` |
| Loading | STD-LOAD |
| Empty | Sections show "not started", never fabricated completeness |
| Error | STD-ERR |
| Recovery | n/a |
| Approval | Per-section status |

**Acceptance criteria**
1. After DEC-010 C1, the view loads with zero errors on a project with research claims.
2. Re-running synthesis never shows duplicate canonical rules (TFD-VER-005).

### S-BIB-02 Visual Language Rules
**Release:** FD-V1 · **Aliases:** P-17 · **Current:** `film_bible.py` rules and synthesis tabs; WF-04 WIP; `POST /film-bible/rules` bypasses approval (G04-D) · **Reqs:** TFD-CIN-010, TFD-CIN-011, TFD-CIN-012, TFD-CIN-013

| Field | Specification |
|---|---|
| Purpose | Define visual rules (category, strictness) and the visual language profile, synthesised or manual, all approved |
| Primary users | Director, Art lead |
| Inputs | Rule text, category (`VisualRuleCategory`), strictness (`RuleStrictness`), linked claim IDs; synthesise trigger |
| Outputs | Approved rules; candidates; conflicts |
| Primary actions | Synthesise (WF-04, async); add rule (candidate); approve selected |
| Secondary actions | Supersede rule; link claim |
| API | `GET/POST /projects/{pid}/film-bible/rules` (exists; target routes POST through approval); `POST /projects/{pid}/workflows/film-bible-synthesis` (exists) |
| Entities | `film_bible_rules`, `film_bible_rule_candidates`, `research_claims` |
| Permissions | `bible.edit`; approve: `canon.approve.visual` |
| Loading | Task status |
| Empty | "No rules yet" |
| Error | Invalid category or strictness → 422 |
| Recovery | Partial approval keeps unselected candidates as `rejected` with notes |
| Approval | Partial approval commits **only** the selected rules (fixes G04-A) |

**Acceptance criteria**
1. Approving 2 of 6 candidates commits exactly 2 rules and stores the decision notes.
2. A rule linked to a claim stores the claim ID. A claim from another tenant is rejected.

---

## 9. Character Studio, Digital Humans, Physical Identity

### S-CHR-01 Character Studio
**Release:** FD-V1 → FD-V2 (reference generation) · **Aliases:** P-14, UX-FD-12 · **Current:** `entities(category=character)` shown in `film_bible.py` entities tab · **Reqs:** TFD-CHR-001…006, TFD-CHR-008, TFD-CHR-009, TFD-DH-010, TFD-VOC-001, TFD-GEN-005, TFD-PRJ-004

| Field | Specification |
|---|---|
| Purpose | Build each character's persistent identity: identity, facial, physical (link), performance, appearance/costume, voice source, mode, and linked performer |
| Primary users | Director, Art lead, Story lead, DH lead |
| Inputs | Profile facets; reference assets with roles (face front/side/¾, expression, performance video); character mode override; voice source; performer link |
| Outputs | Character profile with characteristic-level provenance; versions; scenes in which the character appears |
| Primary actions | Edit (creates a candidate); submit version for approval; link performer |
| Secondary actions | Generate reference sheet (FD-V2, package → S-PKG-02); compare versions; view relationships |
| API | `GET/POST /projects/{pid}/characters`, `GET/PATCH /projects/{pid}/characters/{cid}` (target); `GET /projects/{pid}/characters/{cid}/versions` (target); `GET /projects/{pid}/entities` (exists, legacy) |
| Entities | `characters`, `character_versions`, `character_identity_profiles`, `performance_profiles`, `entities` (legacy link), `assets` |
| Permissions | `character.edit`; approve: `canon.approve.character`; performer references: STD-CONSENT + `identity.view_sensitive` |
| Loading | STD-LOAD |
| Empty | "No characters". Offer extraction from the screenplay (→ S-SCR-02) or manual creation |
| Error | Consent missing → STD-CONSENT block on adding performer references |
| Recovery | STD-RECOVER |
| Approval | Version approval; every characteristic shows `{source, status, confidence, approved_by, version}` |

**Acceptance criteria**
1. Every characteristic displays its provenance. An `estimated` value is never shown as `verified`.
2. A legacy entity character opens in this screen through its link; its original ID still resolves (TFD-CHR-009).
3. Adding a face reference for a linked performer without `reference_storage` consent is blocked, and the block names the purpose.

### S-CHR-02 Character State Timeline
**Release:** FD-V1 · **Aliases:** P-14 (appearance-state timeline) · **Current:** none · **Reqs:** TFD-CHR-007, TFD-CST-003, TFD-CON-002

| Field | Specification |
|---|---|
| Purpose | Scene- and timeline-specific states per character: injury, fatigue, dirt, blood, wetness, damage, ageing, costume state |
| Primary users | Director, Art lead, Continuity |
| Inputs | Matrix of character × scene; state attributes |
| Outputs | State ledger feeding shots and continuity |
| Primary actions | Define state; copy forward; lock (continuity) |
| Secondary actions | Jump to shots using a state |
| API | `GET/POST /projects/{pid}/characters/{cid}/states` (target) |
| Entities | `character_states`, `costume_states`, `scenes` |
| Permissions | `character.edit` |
| Loading | STD-LOAD |
| Empty | "No states defined. Shots will use the base profile." |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | Locking a state sets continuity `approved_canon` (Director) |

**Acceptance criteria**
1. Changing an approved state creates a new version and triggers impact on shots that use it (TFD-CON-008).

### S-DH-01 Performers & Consent
**Release:** FD-V1 (FD-V2 adds submission-time enforcement) · **Aliases:** new · **Current:** none (SEC-12) · **Reqs:** TFD-CNS-001…008, TFD-IAM-007

| Field | Specification |
|---|---|
| Purpose | Register real performers, link them to characters, record purpose-specific consent, and revoke it |
| Primary users | Consent manager (Legal); Producer; DH lead (read) |
| Inputs | Performer identity (minimal personal data per DEC-007); agreement asset; template version; purposes; project scope; validity window |
| Outputs | Consent ledger per performer: purposes × status; dependency list (assets, packages, jobs, digital humans) |
| Primary actions | Add performer; record consent (draft → active on approval); **Revoke** |
| Secondary actions | View dependencies; export consent record |
| API | `GET/POST /performers` (org), `POST /projects/{pid}/performers/{perf_id}/links` (target); `GET/POST /performers/{id}/consents`, `POST /performer-consents/{id}/revoke` (target) |
| Entities | `performers`, `performer_consents`, `assets` (consent document), `approval_requests` (level=consent) |
| Permissions | `consent.manage`; view: `identity.view_sensitive` |
| Loading | STD-LOAD |
| Empty | "No performers. Fictional characters need no consent." |
| Error | Blocked while DEC-012/DEC-007 are unapproved: "Performer data storage is disabled pending policy approval" |
| Recovery | Revocation is idempotent; a partial dependency-flagging failure is retried as a task |
| Approval | Activation needs consent-level approval by a consent manager |

**Acceptance criteria**
1. A consent covering `voice_clone` only does not enable `generated_speech` or `digital_double`.
2. Revocation immediately blocks new gated actions, flags every dependent item `consent_revoked`, and is audited. No audit row is deleted.
3. Users without `identity.view_sensitive` cannot open consent documents.

### S-DH-02 Digital Human & Avatar Workspace
**Release:** FD-V2 · **Aliases:** new · **Current:** none · **Reqs:** TFD-DH-001…009, TFD-OUT-003

| Field | Specification |
|---|---|
| Purpose | Choose and run the digital double / fictional avatar / reusable digital human / transformation workflow per performer↔character |
| Primary users | DH lead, Director |
| Inputs | Avatar mode (digital double / fictional avatar); preserved characteristics; workflow (transformation / reusable DH / both); reference set; rig, motion and costume variants |
| Outputs | Recommendation with rationale; `digital_humans` and `avatar_versions`; transformation inspection results |
| Primary actions | Accept recommendation or choose a workflow; prepare package (→ S-PKG-02); approve avatar version |
| Secondary actions | Import mocap (`movement_references`); request reuse in another project |
| API | `GET/POST /projects/{pid}/digital-humans`, `POST /projects/{pid}/digital-humans/{id}/versions` (target); `POST /projects/{pid}/workflows/dh-recommendation` (target, part of WF-05) |
| Entities | `digital_humans`, `avatar_versions`, `movement_references`, `performer_consents`, `characters` |
| Permissions | `dh.edit`; approve: `canon.approve.character`; irreversible or paid steps: `cost.approve` |
| Loading | Task status |
| Empty | "No digital humans" |
| Error | STD-CONSENT on any missing purpose |
| Recovery | Unknown-outcome jobs follow S-EXE-01 rules |
| Approval | Explicit authorisation for the workflow choice when irreversible (TFD-DH-006) |

**Acceptance criteria**
1. A fictional avatar records which characteristics were preserved. Inspection checks only those plus the approved character spec.
2. A transformation output is compared against the source performance reference for the seven preserved properties (TFD-DH-004).

### S-PHY-01 Physical Identity & Measurements
**Release:** FD-V1 → FD-V2 (scan import, AI estimation) · **Aliases:** new · **Current:** none · **Reqs:** TFD-PHY-001…007

| Field | Specification |
|---|---|
| Purpose | Body profile and measurement records with method, confidence and verification |
| Primary users | DH lead, Costume, Director |
| Inputs | Manual values; corrections; scan import (V2); estimation request (V2) |
| Outputs | Measurements table showing value, unit, method, date, source asset, confidence, verification status, approver and version |
| Primary actions | Add measurement; verify (needs a calibrated method); approve profile |
| Secondary actions | Import scan file; request estimation |
| API | `GET/PUT /projects/{pid}/characters/{cid}/physical-profile`; `GET/POST /projects/{pid}/characters/{cid}/body-measurements`; `POST /projects/{pid}/body-measurements/{mid}/verify` (target) |
| Entities | `physical_identity_profiles`, `body_measurements`, `assets` |
| Permissions | `character.edit`; verify: `measurement.verify`; performer data: STD-CONSENT |
| Loading | STD-LOAD |
| Empty | "No measurements" |
| Error | Verify without a calibrated method → 422 with explanation |
| Recovery | Corrections create new versions |
| Approval | Profile approval; measurement verification is a separate human step |

**Acceptance criteria**
1. An estimate from a single photo is stored as `estimated` with confidence `low` and cannot be verified without a new calibrated capture.
2. Performer measurements cannot be saved without `reference_storage` consent.

---

## 10. Costume, Props, Environment

### S-CST-01 Costume Bible
**Release:** FD-V1 → FD-V2 (reference generation) · **Aliases:** P-15, UX-FD-13 · **Current:** none · **Reqs:** TFD-CST-001, TFD-CST-002, TFD-CST-003, TFD-GEN-011

| Field | Specification |
|---|---|
| Purpose | Define costumes, their states and assignments |
| Primary users | Art lead, Costume |
| Inputs | Garments, armour, accessories, footwear, jewellery, hair/makeup, materials, colours, textures, claims; states; character × scene assignment |
| Outputs | Costume cards, state variants, assignment matrix |
| Primary actions | Create (candidate); approve; assign |
| Secondary actions | Generate reference (V2); link evidence |
| API | `GET/POST /projects/{pid}/costumes`, `/costumes/{id}/states`, `/costume-assignments` (target) |
| Entities | `costumes`, `costume_states`, `characters`, `scenes`, `research_claims` |
| Permissions | `bible.edit`; approve: `canon.approve.visual` |
| Loading | STD-LOAD |
| Empty | "No costumes" |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. A shot's costume resolves from character + scene + state and shows its source.

### S-CST-02 Props & Weapons Register
**Release:** FD-V1 → FD-V2 · **Aliases:** P-15, UX-FD-13 · **Current:** none · **Reqs:** TFD-PRP-001, TFD-PRP-002, TFD-PRP-003, TFD-GEN-011

| Field | Specification |
|---|---|
| Purpose | Register props and weapons, their states, holders and positions per scene |
| Primary users | Art lead, Props |
| Inputs | Kind (prop or weapon); type, design, material, scale, ownership; per-scene states |
| Outputs | Register; state ledger |
| Primary actions | Create; approve; set state |
| Secondary actions | Generate reference (V2) |
| API | `GET/POST /projects/{pid}/props`, `/props/{id}/states` (target) |
| Entities | `props`, `prop_states` |
| Permissions | `bible.edit` |
| Loading | STD-LOAD |
| Empty | "No props" |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. A weapon held in shot N and a missing holder in shot N+1 of the same scene raises a continuity finding (TFD-CON-001).

### S-ENV-01 Locations & Environments
**Release:** FD-V1 → FD-V2 · **Aliases:** P-16, UX-FD-14 · **Current:** `scenes.location_name`; `entities(category=location)` · **Reqs:** TFD-ENV-001…004, TFD-GEN-010

| Field | Specification |
|---|---|
| Purpose | Location and environment bible with states |
| Primary users | Art lead, Director, Cinematographer |
| Inputs | Geography, architecture, layout, terrain, materials, period; states (weather, time of day, change, damage); references |
| Outputs | Location profile; state ledger; reference library |
| Primary actions | Create (or adopt a legacy location); approve; define state |
| Secondary actions | Generate environment reference (V2) |
| API | `GET/POST /projects/{pid}/locations`, `/locations/{id}/environment-states` (target) |
| Entities | `locations`, `environment_profiles`, `environment_states`, `scenes` |
| Permissions | `bible.edit` |
| Loading | STD-LOAD |
| Empty | "No locations". Offers adoption of the N location names found in scenes |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. Adopting the legacy name "Kalinga Battlefield" links every scene with that `location_name` without altering the `scenes` rows' existing columns.

---

## 11. Storyboard, Cinematography, Planning, Method, Capture

### S-SB-01 Storyboard Workbench
**Release:** FD-V1 · **Aliases:** P-07, UX-FD-11 · **Current:** `apps/ui/views/storyboard.py` (panels; generate from text brief via WF-03, deterministic `StoryboardAligner`) · **Reqs:** TFD-SB-001, TFD-SB-002, TFD-SB-004, TFD-SHT-006

| Field | Specification |
|---|---|
| Purpose | Ingest storyboard images or PDFs into panels; order, annotate and approve; convert panels to shot candidates |
| Primary users | Director, Cinematographer |
| Inputs | Storyboard assets; or a text brief (deterministic generator) |
| Outputs | Ordered panels with crops, notes and shot hypotheses |
| Primary actions | Ingest (async); approve panel batch; convert to shot candidates |
| Secondary actions | Reorder; annotate |
| API | `GET /projects/{pid}/storyboard/panels` (exists); `POST /projects/{pid}/workflows/storyboard-intelligence` (exists); `POST /projects/{pid}/storyboard/ingestions` (target) |
| Entities | `storyboard_panels`, `storyboard_panel_candidates`, `assets` |
| Permissions | `storyboard.edit`; approve: `canon.approve.story` |
| Loading | Task status |
| Empty | "Upload storyboard pages or generate panels from a brief" |
| Error | A per-page extraction failure keeps the other pages |
| Recovery | Re-ingest a single page |
| Approval | Existing partial approval |

**Acceptance criteria**
1. A 12-page PDF yields panel candidates per page, each with a crop asset and a page locator.
2. Text-brief panels show the `deterministic` label.

### S-SB-02 Script ↔ Storyboard Alignment
**Release:** FD-V1 · **Aliases:** P-08 · **Current:** single `storyboard_panels.scene_id` FK · **Reqs:** TFD-SB-003

| Field | Specification |
|---|---|
| Purpose | Many-to-many mapping of panels to scenes and shots, with unmatched beats |
| Primary users | Director, Story lead |
| Inputs | Mapping edits |
| Outputs | Two-pane view; unmatched scenes and panels; conflicts |
| Primary actions | Map / unmap; approve mapping |
| Secondary actions | Create a shot from an unmatched panel |
| API | `GET/POST /projects/{pid}/storyboard/mappings` (target) |
| Entities | panel↔scene↔shot mapping, `storyboard_panels`, `scenes`, `shots` |
| Permissions | `storyboard.edit` |
| Loading | STD-LOAD |
| Empty | "No mappings" |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. One panel can map to two scenes, and one scene to many panels.
2. The existing `scene_id` values are backfilled as mappings.

### S-CIN-01 Cinematography Bible & Libraries
**Release:** FD-V1 · **Aliases:** P-17 (camera language) · **Current:** `VisualRuleCategory.CAMERA_LANGUAGE`; hardcoded lens notes in `aligner.py` · **Reqs:** TFD-CIN-005, TFD-CIN-006

| Field | Specification |
|---|---|
| Purpose | Project camera package, lens library, lighting library, composition rules, virtual camera profile, visual language profile |
| Primary users | Cinematographer, Director |
| Inputs | Profiles with extensible parameters |
| Outputs | Versioned cinematography bible used as defaults by S-SHT-01 |
| Primary actions | Add profile; approve bible version |
| Secondary actions | Duplicate profile; mark default |
| API | `GET/PUT /projects/{pid}/cinematography/profile`; `GET/POST /projects/{pid}/camera-profiles`, `/lens-profiles`, `/lighting-profiles` (target) |
| Entities | `cinematography_profiles`, `camera_profiles`, `lens_profiles`, `lighting_profiles` |
| Permissions | `cinematography.edit`; approve: `canon.approve.visual` |
| Loading | STD-LOAD |
| Empty | "No camera package. Shots can still be specified directly." |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. A user-defined lens parameter (for example, "anamorphic squeeze 1.8x") is saved and shown without schema change (TFD-CIN-001).

### S-SEQ-01 Sequence Planner
**Release:** FD-V1 · **Aliases:** P-19, UX-FD-16 · **Current:** none · **Reqs:** TFD-SEQ-001, TFD-PRJ-004, TFD-SCR-009

| Field | Specification |
|---|---|
| Purpose | Group scenes into sequences with goal, emotion and mode override |
| Primary users | Director |
| Inputs | Scene selection; goal; emotion; mode override |
| Outputs | Ordered sequences with effective mode and screenplay version |
| Primary actions | Create; reorder; approve |
| Secondary actions | Set mode override (→ S-MTH-01 shows the cascade) |
| API | `GET/POST /projects/{pid}/sequences`, `PATCH /projects/{pid}/sequences/{id}` (target) |
| Entities | `sequences`, `scenes` |
| Permissions | `planning.edit`; approve: `canon.approve.plan` |
| Loading | STD-LOAD |
| Empty | "No sequences". Social and reel templates explain that sequences are optional |
| Error | Scene from a superseded screenplay version → `review_required` badge |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. A sequence created against screenplay v2 shows "based on v2" after v3 is locked, and is flagged `review_required` if it is affected.

### S-SEQ-02 Scene Planner
**Release:** FD-V1 · **Aliases:** P-20 · **Current:** canonical `scenes` (read-only today) · **Reqs:** TFD-SEQ-002, TFD-PRJ-004

| Field | Specification |
|---|---|
| Purpose | Prepare a scene: creative intention, entry and exit states, mode override |
| Primary users | Director, Cinematographer |
| Inputs | Intention; character, costume, prop and environment states in/out; mode |
| Outputs | Scene plan |
| Primary actions | Save plan; create shot list (→ S-SHT-01) |
| Secondary actions | View the script passage |
| API | `GET /projects/{pid}/scenes` (exists); `PATCH /projects/{pid}/scenes/{sid}/plan` (target) |
| Entities | `scenes`, `character_states`, `environment_states` |
| Permissions | `planning.edit` |
| Loading | STD-LOAD |
| Empty | n/a |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. A scene plan never edits scene text derived from the locked screenplay.

### S-SHT-01 Shot Planner & Shot Spec
**Release:** FD-V1 · **Aliases:** P-21, UX-FD-17 · **Current:** `storyboard_panels.shot_type` only · **Reqs:** TFD-SHT-001…005, TFD-CIN-001…004, TFD-PRJ-004, TFD-PRJ-005

| Field | Specification |
|---|---|
| Purpose | Define each shot: type, composition, action, duration, states, references, production method, camera spec (physical or virtual, with origin), and request recommendations |
| Primary users | Director, Cinematographer |
| Inputs | Shot fields; intent description for recommendations; overrides |
| Outputs | Versioned Shot Spec (provider-neutral); recommendation with rationale; mode conflict findings |
| Primary actions | Add shot; Recommend (WF-06, async); accept or override a field; set production method; submit for approval |
| Secondary actions | Compile (→ S-PKG-02); plan capture (→ S-CAP-01); view continuity |
| API | `GET/POST /projects/{pid}/scenes/{sid}/shots`, `GET/PATCH /projects/{pid}/shots/{id}` (target); `POST /projects/{pid}/workflows/shot-planning` (target, WF-06) |
| Entities | `shots` (`camera_spec` JSONB, `spec_kind`, `metadata_origin`, `production_mode`, `production_method`, `screenplay_version_id`, `shot_spec_schema_version`), `character_states`, `assets` |
| Permissions | `planning.edit`; approve: `canon.approve.plan` |
| Loading | Recommendation shows the real task stage |
| Empty | "No shots. Add manually, convert storyboard panels, or ask for a recommendation." |
| Error | Method not allowed for the effective mode → inline `mode_conflict` with resolve options |
| Recovery | Recommendations never overwrite fields; they appear as suggestions per field |
| Approval | Approved shot spec is immutable; edits create a new version |

**Acceptance criteria**
1. Every camera value displays `actual`, `creative_target` or `recommended`. A recommendation never fills a field as `actual`.
2. Each recommendation shows its rationale; override is recorded with the user.
3. Packaging is blocked until `production_method` is set and valid for the effective mode.

### S-MTH-01 Production Mode & Method Map
**Release:** FD-V1 · **Aliases:** new · **Current:** none · **Reqs:** TFD-PRJ-003, TFD-PRJ-004, TFD-PRJ-005, TFD-PRJ-006, TFD-SHT-002

| Field | Specification |
|---|---|
| Purpose | See and change production mode at project → sequence → scene → shot, and character constraints; set methods in bulk |
| Primary users | Director, Producer |
| Inputs | Mode overrides at any level; bulk method assignment |
| Outputs | Tree or table showing effective mode, inheritance source, method, and conflicts; counts by method |
| Primary actions | Set or clear an override; bulk set method; resolve conflict |
| Secondary actions | Filter to hybrid shots (→ S-CAP-01) |
| API | `GET /projects/{pid}/production-mode-map` (target); `PATCH` mode on `/sequences/{id}`, `/scenes/{sid}`, `/characters/{cid}`, `/shots/{id}` (target) |
| Entities | `projects`, `sequences`, `scenes`, `characters`, `shots`, `creative_decisions`, `impact_analyses` |
| Permissions | `planning.edit`; changes affecting approved shots: Director |
| Loading | STD-LOAD |
| Empty | "Project mode: X. No overrides." |
| Error | STD-ERR |
| Recovery | An override change shows the impact preview before commit |
| Approval | Overrides outside the allowed method set need a `creative_decision` with rationale |

**Acceptance criteria**
1. Clearing a scene override makes its shots inherit from the sequence, and the source label updates.
2. A character set to `hybrid_live_action` in a `fully_ai_generated` shot shows a conflict. Nothing auto-changes.

### S-CAP-01 Capture Plan & Manifest
**Release:** FD-V2 · **Aliases:** new · **Current:** none · **Reqs:** TFD-HYB-001, TFD-HYB-002, TFD-HYB-004

| Field | Specification |
|---|---|
| Purpose | Generate scene- and shot-specific capture instructions and the capture manifest for a shoot |
| Primary users | On-set/VFX supervisor, Cinematographer, Director |
| Inputs | Shots with hybrid methods; environment; movement; target provider requirements |
| Outputs | Capture plan (every Master §8.1 item applicable to the shot); manifest (§8.3 fields); printable call-sheet export |
| Primary actions | Generate plan (WF-12, async); edit; approve manifest |
| Secondary actions | Export PDF/CSV for set; link captured footage |
| API | `POST /projects/{pid}/workflows/capture-plan` (target, WF-12); `GET/POST /projects/{pid}/capture-plans`, `/capture-manifests`, `POST …/capture-manifests/{id}/footage-links` (target) |
| Entities | `capture_plans`, `capture_requirements`, `capture_manifests`, `production_footage`, `shots`, `performers` |
| Permissions | `capture.edit`; approve: `canon.approve.plan` |
| Loading | Task status |
| Empty | "No shots use a live-action or transformation method" |
| Error | Missing provider requirements → plan marked `incomplete` with the missing inputs |
| Recovery | Regeneration creates a new plan version |
| Approval | Manifest approval status per §8.3 |

**Acceptance criteria**
1. Two shots with different camera movement and method produce different requirement sets. There is no uniform template.
2. Manifest items show `required / captured / validated / missing`.

### S-CAP-02 Footage Ingestion & Analysis
**Release:** FD-V2 · **Aliases:** new · **Current:** none · **Reqs:** TFD-HYB-003, TFD-HYB-004, TFD-HYB-005

| Field | Specification |
|---|---|
| Purpose | Ingest independently shot footage and get practical recommendations |
| Primary users | On-set/VFX supervisor, Director |
| Inputs | Footage files; optional manifest and shot link |
| Outputs | Issues (Master §8.2 list), each with method label and coverage; actual camera metadata; recommendations |
| Primary actions | Upload; analyse (WF-13, async); accept footage for shot |
| Secondary actions | Mark issue acceptable; request reshoot item |
| API | `POST /projects/{pid}/footage` (target, uses upload flow); `POST /projects/{pid}/workflows/footage-analysis` (target, WF-13) |
| Entities | `production_footage`, `assets`, `capture_manifests`, `shots` |
| Permissions | `capture.edit`; performer footage: STD-CONSENT (`performance_transformation` when used as source) |
| Loading | Proxy generation, then analysis stages |
| Empty | "No footage" |
| Error | An unanalysable check is shown as "not assessed", never as "pass" |
| Recovery | Per-check retry |
| Approval | Footage acceptance per shot by the Director |

**Acceptance criteria**
1. Footage with mixed frame rates is flagged from container metadata with method `metadata`.
2. No footage is rejected automatically; every issue offers a recommendation.

---

## 12. Prompt & Handoff, Execution, Output, Library

### S-PKG-01 Master Direction
**Release:** FD-V1 (P1) · **Aliases:** P-26 · **Current:** none · **Reqs:** TFD-PKG-005

| Field | Specification |
|---|---|
| Purpose | Project-level direction sections consumed by the compiler |
| Primary users | Director |
| Inputs | Sections (tone, look, constraints, exclusions) |
| Outputs | Versioned master direction |
| Primary actions | Edit; approve |
| Secondary actions | Compare versions |
| API | `GET/PUT /projects/{pid}/master-direction` (target) |
| Entities | Master direction artifact |
| Permissions | `direction.edit`; approve: Director |
| Loading | STD-LOAD |
| Empty | "Optional. The compiler uses the Film Bible and Cinematography Bible alone." |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. Packages record the master direction version they used.

### S-PKG-02 Shot Package Compiler
**Release:** FD-V1 → FD-V2 · **Aliases:** P-27, P-28, UX-FD-20 · **Current:** none · **Reqs:** TFD-SHT-003, TFD-PKG-001…004, TFD-PKG-006, TFD-PKG-007, TFD-CTX-001, TFD-CTX-003

| Field | Specification |
|---|---|
| Purpose | Compile an approved Shot Spec + context into a target-specific prompt and an immutable package; validate; see staleness |
| Primary users | Production operator, Director |
| Inputs | Approved shot (or character/environment/costume target for reference packages); target tool (registry entry or manual target); tool recommendation |
| Outputs | Prompt layers; settings; reference manifest (asset version, checksum, role, rights and consent status); validation report; context used and excluded; package hash |
| Primary actions | Compile (WF-09, async); accept the recommended tool or choose one manually |
| Secondary actions | Edit prompt (creates a new prompt version with an audit trail); recompile when stale |
| API | `POST /projects/{pid}/shots/{id}/packages` (target, starts WF-09); `GET /projects/{pid}/packages/{pkg_id}` (target); `GET /projects/{pid}/context-packages/{id}` (target); `GET /providers/{id}/snapshots` (target) |
| Entities | `production_packages`, `prompt_versions`, `context_packages`, `shots`, `provider_capability_snapshots` |
| Permissions | `package.compile` |
| Loading | Task status |
| Empty | "Approve the shot spec to compile" |
| Error | Validation failures list each unsupported parameter, and export is blocked. Consent missing → STD-CONSENT |
| Recovery | Stale package → banner with the changed source → Recompile (new version; the old one is kept) |
| Approval | Package approval (creative) before export or submit |

**Acceptance criteria**
1. Compiling twice from identical inputs yields an identical content hash.
2. Changing an approved costume state used by the shot marks the package `stale`.
3. The core Shot Spec in the package contains no provider-specific fields outside the typed extension.

### S-PKG-03 Handoff: Manual Export / Connected Submit
**Release:** FD-V1 (manual) → FD-V2 (connected) · **Aliases:** P-29, UX-FD-20 · **Current:** none (`higgsfield_integration_mode="manual_export"` config only) · **Reqs:** TFD-INT-001, TFD-INT-002, TFD-INT-004, TFD-INT-008, TFD-GEN-004, TFD-CNS-007, TFD-CNS-008

| Field | Specification |
|---|---|
| Purpose | Execute an approved package: manual (copy and download) or connected (submit) |
| Primary users | Production operator |
| Inputs | Approved package; execution mode (enabled modes only); for connected mode: cost estimate acknowledgement and data-disclosure acknowledgement |
| Outputs | Manual: copied prompt and settings, downloaded JSON + Markdown manifest and ZIP/links, plus an export record. Connected: a job with an attempt |
| Primary actions | Copy prompt; Download package; Mark as exported; (V2) Submit |
| Secondary actions | Open the external tool (link only); switch to manual |
| API | `POST /projects/{pid}/packages/{pkg_id}/export` (target); `POST /projects/{pid}/packages/{pkg_id}/submit` (target, V2, needs `Idempotency-Key`) |
| Entities | `production_packages`, `generation_jobs`, `generation_attempts`, `generation_cost_records`, `approval_requests` (level=cost) |
| Permissions | Export: `package.export`; submit: `provider.submit`; spend: `cost.approve` |
| Loading | Submit shows the real step (validate → consent → cost → submit) |
| Empty | n/a |
| Error | Provider unavailable → offer manual export of the same package. Never auto-duplicate |
| Recovery | Timeout → `unknown_outcome` → reconcile in S-EXE-01 |
| Approval | Cost approval (`approval_level=cost`) with model, action and estimate (or "cost unknown") before submit |

**Acceptance criteria**
1. With every connector disabled, a package can be copied, downloaded and recorded as exported (TFD-INT-001).
2. Exports never contain credentials or long-lived URLs.
3. Manual mode is never styled as an error or a fallback warning.

### S-EXE-01 Execution Monitor
**Release:** FD-V1 (manual export history) → FD-V2 (jobs, attempts, cost) · **Aliases:** P-30, UX-FD-22 · **Current:** none · **Reqs:** TFD-GEN-001, TFD-GEN-002, TFD-GEN-003, TFD-GEN-008, TFD-GEN-009

| Field | Specification |
|---|---|
| Purpose | Track every package execution: manual exports awaiting import, and connected jobs with attempts and cost |
| Primary users | Production operator, Producer |
| Inputs | Filters: shot, provider, mode, state |
| Outputs | Rows showing package version, mode, state, provider request ID, attempts, estimated vs actual cost, and linked outputs |
| Primary actions | Import results (→ S-EXE-02); reconcile unknown outcome; cancel |
| Secondary actions | Retry (only after reconciliation) |
| API | `GET /projects/{pid}/generation-jobs` (target); `POST /projects/{pid}/generation-jobs/{id}/reconcile`, `/cancel` (target) |
| Entities | `generation_jobs`, `generation_attempts`, `generation_cost_records`, `production_packages` |
| Permissions | Read: project; reconcile and cancel: `provider.submit` |
| Loading | Polling |
| Empty | "No executions yet" |
| Error | Error class per attempt |
| Recovery | Unknown outcome: reconcile by provider request ID or account history. Retry stays disabled until reconciled |
| Approval | Re-submission after a failure needs a new cost approval |

**Acceptance criteria**
1. A manual export appears as `manual_exported → awaiting_import`, with the same row structure as connected jobs (TFD-GEN-008).
2. A job in `unknown_outcome` shows no Retry action.

### S-EXE-02 Output Import & Mapping
**Release:** FD-V1 · **Aliases:** P-31 (import) · **Current:** generic upload only · **Reqs:** TFD-OUT-001, TFD-OUT-006

| Field | Specification |
|---|---|
| Purpose | Import results from external tools and map them to their package, shot and entities |
| Primary users | Production operator |
| Inputs | Files; package or job (pre-selected when coming from S-EXE-01); mapping; optional external metadata (labelled `user_supplied`) |
| Outputs | Immutable output assets linked to package, job, shot and entities |
| Primary actions | Upload; map; confirm |
| Secondary actions | Split one file across several shots |
| API | `POST /projects/{pid}/import-jobs` (target); `POST /projects/{pid}/import-jobs/{id}/mappings` (target) |
| Entities | `import_jobs`, `assets`, `asset_lineage`, `generation_jobs` |
| Permissions | `output.import` |
| Loading | Per-file state |
| Empty | Shows exports awaiting import |
| Error | Per-file validation errors |
| Recovery | Unmapped files stay in `awaiting_mapping` and are never discarded |
| Approval | None at import; review happens in S-OUT-01 |

**Acceptance criteria**
1. Imported files are new assets; no earlier output is overwritten.
2. A missing provider job ID stays empty or `user_supplied` and is never invented.

### S-OUT-01 Output Inspector & Revision
**Release:** FD-V1 (human checklist) → FD-V2 (AI-assisted, continuity comparison, regeneration) · **Aliases:** P-31, P-32, UX-FD-23 · **Current:** none · **Reqs:** TFD-OUT-002, TFD-OUT-003, TFD-OUT-004, TFD-OUT-005, TFD-CON-007

| Field | Specification |
|---|---|
| Purpose | Inspect an output against its Shot Spec and approved references; approve, reject or request revision |
| Primary users | Director, Production operator |
| Inputs | Output asset; Stage 13 checklist (identity, face, body, movement, costume, environment, lighting, composition, camera, lip-sync, artifacts, continuity, quality) |
| Outputs | Findings with severity, evidence (timecode or frame) and method label; disposition; revision request |
| Primary actions | Approve; Reject; Request revision (→ new package version) |
| Secondary actions | A/B compare with references; (V2) run AI inspection (WF-11) |
| API | `POST /projects/{pid}/output-reviews` (target); `POST /projects/{pid}/revision-requests` (target); `POST /projects/{pid}/workflows/output-inspection` (target, WF-11, V2) |
| Entities | `output_reviews`, `revision_requests`, `continuity_findings`, `assets` |
| Permissions | `output.review`; approve: `output.approve` |
| Loading | Proxy media; inspection stages |
| Empty | "Nothing to inspect" |
| Error | Unsupported media shows a metadata-only view |
| Recovery | A revision request keeps the original output and its findings |
| Approval | Approval creates a versioned approved output artifact |

**Acceptance criteria**
1. Requesting a revision creates a new package version linked to the finding. The prior package and output stay intact (TFD-OUT-005).
2. AI findings (V2) show method and coverage. Unassessed dimensions are listed as such.

### S-LIB-01 Production Asset Library
**Release:** FD-V2 · **Aliases:** new · **Current:** none · **Reqs:** TFD-LIB-001, TFD-LIB-002

| Field | Specification |
|---|---|
| Purpose | Approved production assets organised by shot, scene, character and location (Stage 15) |
| Primary users | Director, Producer, Post |
| Inputs | Filters (asset type, shot, scene, character, status) |
| Outputs | Library grid; lineage panel (package → job/attempt → provider/model/params → review) |
| Primary actions | Open lineage; add to post handoff |
| Secondary actions | Share to org library |
| API | `GET /projects/{pid}/library` (target); `GET /projects/{pid}/assets/{aid}/lineage` (target) |
| Entities | `assets`, `asset_lineage`, `output_reviews`, `generation_jobs` |
| Permissions | `project.read` |
| Loading | Thumbnail proxies |
| Empty | "No approved outputs" |
| Error | STD-ERR |
| Recovery | n/a |
| Approval | Shows approval version and approver |

**Acceptance criteria**
1. Every item shows complete lineage, or an explicit "user_supplied / unknown" marker per missing link.

---

## 13. Continuity, AI Director

### S-CON-01 Continuity Overview & Rules
**Release:** FD-V1 · **Aliases:** P-22, UX-FD-18 · **Current:** none · **Reqs:** TFD-CON-001…006

| Field | Specification |
|---|---|
| Purpose | Configure rules per dimension, run checks, and see findings with coverage |
| Primary users | Director, Continuity supervisor |
| Inputs | Rules (lock, permitted variation bounds, scene- and timeline-specific states); check scope |
| Outputs | Findings by dimension and severity; coverage statement; status per rule (9 states) |
| Primary actions | Run check (WF-07, async); lock characteristic; permit variation |
| Secondary actions | Graph or list lens |
| API | `GET/POST /projects/{pid}/continuity/rules`; `POST /projects/{pid}/workflows/continuity-check` (target, WF-07); `GET /projects/{pid}/continuity/findings` (target) |
| Entities | `continuity_rules`, `continuity_findings`, `continuity_decisions` |
| Permissions | `continuity.edit`; decisions: Director |
| Loading | Task status |
| Empty | "Not configured", which is a valid state |
| Error | Partial check → partial coverage shown |
| Recovery | Re-run only the missing scope |
| Approval | Rules move `candidate → review_required → approved_canon` by the Director |

**Acceptance criteria**
1. A run with no findings displays the dimensions, shots and methods covered, and never "all consistent".
2. Checks span real-footage and AI shots in the same sequence (TFD-CON-004).

### S-CON-02 Continuity Finding Detail
**Release:** FD-V1 · **Aliases:** P-23 · **Current:** none · **Reqs:** TFD-CON-002, TFD-CON-003, TFD-CON-006

| Field | Specification |
|---|---|
| Purpose | Resolve one finding: expected vs observed, evidence, impact |
| Primary users | Director |
| Inputs | Disposition (intentional variation / request correction / reject finding) with rationale |
| Outputs | `continuity_decisions` row; status transition |
| Primary actions | Decide |
| Secondary actions | Open the affected shot or output |
| API | `POST /projects/{pid}/continuity/findings/{id}/decision` (target) |
| Entities | `continuity_findings`, `continuity_decisions` |
| Permissions | `continuity.decide` (Director) |
| Loading | STD-LOAD |
| Empty | n/a |
| Error | STD-ERR |
| Recovery | STD-RECOVER |
| Approval | Director only; AI cannot set `intentional_variation` |

**Acceptance criteria**
1. Every disposition stores the actor and rationale; a rejected finding remains auditable.

### S-CON-03 Change Impact Analysis
**Release:** FD-V1 · **Aliases:** UX-FD-18 (impact), IA §3.2 H · **Current:** none · **Reqs:** TFD-CON-008, TFD-SCR-010, TFD-PRJ-006, TFD-CNS-004

| Field | Specification |
|---|---|
| Purpose | Show what a change affects (screenplay revision, character, date, environment, mode, consent revocation) and drive review |
| Primary users | Director, Management (for screenplay), Consent manager (for revocation) |
| Inputs | Source change |
| Outputs | Affected scenes, characters, sequences, shots, assets, packages, localised dialogue and jobs, each with review status |
| Primary actions | Mark reviewed / needs rework per item |
| Secondary actions | Export list |
| API | `GET /projects/{pid}/impact-analyses/{id}` (target); `POST /projects/{pid}/impact-analyses/{id}/items/{item_id}/review` (target) |
| Entities | `impact_analyses`, dependency edges, `review_required` markers |
| Permissions | Read: project; review: owner capability of each item |
| Loading | Computed as a task |
| Empty | "No downstream items affected" (with scope) |
| Error | STD-ERR |
| Recovery | Recompute on demand |
| Approval | Items clear `review_required` only through their owner's action |

**Acceptance criteria**
1. Approving a screenplay revision that deletes scene 12 lists every shot and package of scene 12 as affected, and none of them changes automatically.

### S-AID-01 AI Director Review
**Release:** FD-V1 · **Aliases:** P-24, P-25, UX-FD-19 · **Current:** none · **Reqs:** TFD-AID-001, TFD-AID-003, TFD-AID-006, TFD-CTX-004

| Field | Specification |
|---|---|
| Purpose | Prioritised findings and recommendations across the project, scene or shot, with human disposition |
| Primary users | Director |
| Inputs | Scope; review trigger |
| Outputs | Findings (severity, confidence, evidence, affected items, context used); recommendation detail with before and after |
| Primary actions | Run review (WF-08, async); accept, edit, reject or defer |
| Secondary actions | Request research (→ S-RES-02) |
| API | `POST /projects/{pid}/workflows/ai-director-review` (target, WF-08); `GET /projects/{pid}/ai-director/findings`, `POST …/findings/{id}/disposition` (target) |
| Entities | `ai_runs`, findings, `context_packages`, `creative_decisions` |
| Permissions | Run: `review.request`; dispose: Director |
| Loading | Task status |
| Empty | "No review run" |
| Error | Partial review → completed scope shown |
| Recovery | Re-run missing scope |
| Approval | Accepting a recommendation creates a candidate on the target object. It never writes canon |

**Acceptance criteria**
1. Accepting a recommendation produces a candidate requiring the normal approval for its domain.

---

## 14. Voice & Dialogue

### S-VOC-01 Dialogue & Voice Studio
**Release:** FD-V2 · **Aliases:** IA §3.2 E "Audio / Voice / Sound References" · **Current:** none · **Reqs:** TFD-VOC-001, TFD-VOC-002, TFD-VOC-003, TFD-VOC-004

| Field | Specification |
|---|---|
| Purpose | Per dialogue segment: original takes or authorised AI voice; voice profiles; delivery settings |
| Primary users | Voice lead, Director |
| Inputs | Recordings (takes); voice source per character or scene; voice profile; emotion and delivery; language and accent |
| Outputs | Segment × take matrix; selected take or voice package; quality and sync status |
| Primary actions | Upload takes; select take; create voice profile; compile voice package (→ S-PKG-02) |
| Secondary actions | Compare takes |
| API | `GET /projects/{pid}/dialogue-segments` (target); `POST /projects/{pid}/dialogue-segments/{id}/takes`; `GET/POST /projects/{pid}/voice-profiles` (target) |
| Entities | `dialogue_segments`, `voice_profiles`, `assets` (audio), `performer_consents` |
| Permissions | `voice.edit`; voice clone or generated speech: STD-CONSENT |
| Loading | Waveform proxy |
| Empty | "No recordings" |
| Error | Consent missing → block naming `voice_clone` or `generated_speech` |
| Recovery | STD-RECOVER |
| Approval | Voice profile and selected take approvals |

**Acceptance criteria**
1. A performer with recorded-audio consent only cannot have a voice profile of type `clone` created.
2. Segment text is read-only (from the locked screenplay).

### S-VOC-02 Localisation & Dubbing
**Release:** FD-V2 · **Aliases:** new · **Current:** none · **Reqs:** TFD-VOC-005, TFD-VOC-006, TFD-VOC-007

| Field | Specification |
|---|---|
| Purpose | Localised scripts as separate approved assets; dubbing and lip-sync via external tools; timing validation; dialogue comparison |
| Primary users | Voice/localisation lead |
| Inputs | Target language; translated lines; dubbing package; lip-sync results |
| Outputs | Localised script versions linked to screenplay version and segments; timing validation |
| Primary actions | Create localised script; approve; prepare dub or lip-sync package |
| Secondary actions | Compare original / translation / generated |
| API | `GET/POST /projects/{pid}/localised-scripts` (target) |
| Entities | Localised script artifacts, `dialogue_segments`, `screenplay_versions` |
| Permissions | `voice.edit`; approve: `canon.approve.localisation` |
| Loading | STD-LOAD |
| Empty | "No localisations" |
| Error | Source screenplay superseded → `review_required` |
| Recovery | STD-RECOVER |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. Creating or approving a localisation leaves the locked screenplay dialogue unchanged.

---

## 15. Approval & Version History, Post

### S-APR-02 Approval Detail
**Release:** FD-V1 · **Aliases:** G-05 detail, UX-FD-24 · **Current:** `review.py` decision form → `POST /approvals/{id}/decide` (locks row `for_update`, commits before resume) · **Reqs:** TFD-APR-001, TFD-APR-003, TFD-APR-004, TFD-APR-005, TFD-APR-007

| Field | Specification |
|---|---|
| Purpose | Decide one approval with full context |
| Primary users | Approvers |
| Inputs | Selection (partial), decision, notes |
| Outputs | Decision; canonical commit or rejection; version bump |
| Primary actions | Approve selected; reject; request changes |
| Secondary actions | View diff, evidence and impact |
| API | `GET /approvals/{id}` (target); `POST /approvals/{id}/decide` (exists; body adds `target_version`) |
| Entities | `approval_requests`, candidate tables, `project_versions`, `audit_events` |
| Permissions | `required_capability` of the request |
| Loading | STD-LOAD |
| Empty | n/a |
| Error | 409 stale version → re-review; 422 unknown scope |
| Recovery | Decision committed before graph resume. A resume failure leaves the decision recorded and the task retryable |
| Approval | STD-APPROVAL |

**Acceptance criteria**
1. Deciding with an outdated `target_version` returns 409 and commits nothing.
2. The recorded actor equals the authenticated user.

### S-APR-03 Versions, Decisions & Audit
**Release:** FD-V1 · **Aliases:** P-33, UX-FD-24 · **Current:** `apps/ui/views/audit.py` (event list); `film_bible.py` versions tab; `GET /projects/{pid}/versions`, `/audit-log` (exist) · **Reqs:** TFD-VER-001…004, TFD-AUD-001, TFD-AUD-003

| Field | Specification |
|---|---|
| Purpose | Project version history, artifact versions and relationships, decisions, audit trail |
| Primary users | Producer, Director, Admin |
| Inputs | Filters (actor, action, object, date) |
| Outputs | Versions; derived_from/supersedes graph; audit events |
| Primary actions | Open version; export audit |
| Secondary actions | — |
| API | `GET /projects/{pid}/versions`, `/audit-log` (exist; target adds pagination and filters); `GET /projects/{pid}/audit-log/export` (target) |
| Entities | `project_versions`, artifact version tables, `audit_events` |
| Permissions | Audit export: `audit.export` |
| Loading | STD-LOAD |
| Empty | "Project created" event always present |
| Error | STD-ERR |
| Recovery | n/a |
| Approval | Read-only |

**Acceptance criteria**
1. Version numbers are unique per project under concurrent approvals (TFD-VER-001).
2. No UI or API path edits or deletes an audit event.

### S-APR-04 Branch Compare — DEFERRED
**Aliases:** P-34. Deferred by **DEC-029**; not built in FD-V1 or FD-V2. Alternatives are handled by S-SCR-04 suggestions and S-SCR-03 draft revisions.

### S-PST-01 Exports & Post-Production Handoff
**Release:** FD-V1 (project archive) → FD-V2 (post handoff package) · **Aliases:** P-35 · **Current:** none · **Reqs:** TFD-POST-001…004

| Field | Specification |
|---|---|
| Purpose | Export the project archive (V1) and assemble post handoff packages (V2) |
| Primary users | Producer, Post coordinator; external editor (download) |
| Inputs | Scope (episode, sequences, shots); format (JSON + CSV manifest + media folder; others shown as "not supported" until validated) |
| Outputs | Archive or handoff package with manifest, checksums and provenance |
| Primary actions | Build; download (signed URL) |
| Secondary actions | Add editorial notes |
| API | `POST /projects/{pid}/exports` (target, archive); `POST /projects/{pid}/post-handoffs` (target, V2); `GET …/{id}/download-url` |
| Entities | Exports, post handoff manifest, `assets`, `shots`, `dialogue_segments` |
| Permissions | `export.create`; external download via a time-limited link issued by a member |
| Loading | Build task |
| Empty | "No approved outputs to hand off" |
| Error | Missing items listed (for example, a shot with no approved output) |
| Recovery | Rebuild creates a new export version |
| Approval | Handoff package approval by the Producer before external share |

**Acceptance criteria**
1. OTIO, EDL, XML and AAF options are not selectable until marked validated (DEC-014).
2. The manifest lists every §11 field for each shot, with "not available" where timecode is missing.

---

## 16. Screen ↔ requirement coverage check

Every FD-V1 and FD-V2 requirement in `PRD_v1.0.md` §14 that has user-facing behaviour is referenced by at least one screen above.

Requirements with **no dedicated screen** are backend or operational. They are verified through API and system tests rather than a screen:
- TFD-IAM-001 (auth, surfaced via STD-ERR 401)
- TFD-IAM-009
- TFD-AST-008
- TFD-CTX-002
- TFD-AID-002, 004, 005, 007
- TFD-AUD-002, 004
- TFD-OPS-002, 003, 004, 006, 007, 008, 010
- TFD-INT-006 (surfaced as a registry flag)
- TFD-INT-007, 009
- TFD-VER-005
- TFD-FMT-001 (surfaced in S-GLB-02)
