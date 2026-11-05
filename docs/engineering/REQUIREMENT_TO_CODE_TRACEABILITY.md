# Requirement-to-Code Traceability Matrix

**Doc ID:** TFD-ENG-011 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval
**Inputs:** Master Prompt §15 (55 V1/V2 items), §28 · `docs/product/PRD_v1.0.md` (requirement IDs, text, release, current status) · `docs/product/INFORMATION_ARCHITECTURE.md` (screen IDs `S-*`) · `docs/architecture/API_AND_EVENT_CONTRACTS.md` (target routes) · `docs/architecture/DATABASE_DESIGN_AND_ERD.md` (target tables) · `docs/audit/02` (status evidence) · Gap Report §12 (FD-FR-001…060) · code under `apps/`, `packages/`, `tests/`

---

## 1. How to read this matrix

- **One matrix** (Master Prompt §28 "Maintain one traceability matrix"). Every requirement in PRD v1.0 appears exactly once: **224 IDs across 33 areas**. That covers all 55 Master Prompt §15 items (coverage check in §3) and the new families (production mode, formats, consent, digital humans, on-set and hybrid capture, voice, post handoff).
- **IDs** follow DEC-011: `TFD-<AREA>-nnn`. The PRD is the owner of IDs and requirement text; this matrix is generated from the PRD table. If the PRD changes, this matrix is regenerated, not hand-edited.
- **Current-code columns** (Screen, API, Service, Workflow, DB, Audit/version, Test) contain **real paths in the repository today** (`main@b3621cb` + uncommitted G-04 WIP), or `—` when nothing exists. The **target** for each column is given per area in §2, so the matrix rows do not repeat it.
- **Design columns** (User story, Journey, Domain model) describe the target. Journeys reference the Master Prompt §13 stages (`§13-S1` … `§13-S16`).
- **Status** is copied from the PRD, which takes it from `docs/audit/02`: `VERIFIED` (deterministic/mocked, local tests only), `PARTIAL`, `MOCKED`, `SCAFFOLD`, `BROKEN`, `DEFECT`, `NOT_IMPL`, `n/a` (migration or policy requirement with no runtime feature).
- **Aliases:** the §15 item (`V1-nn` / `V2-nn`), Gap Report `FD-FR-nnn`, PRD v0.9 / IA references (`UX-FD-*`, `AC-*`), and legacy graph IDs `G-0x` mapped to `WF-nn` (DEC-011: G-01 Script Intelligence = WF-01, G-02 Historical Research = WF-02, G-03 Storyboard = WF-03, G-04 Film Bible = WF-04, then WF-05 Character/Asset … WF-11 Output Inspection).
- **Test column convention:** a requirement becomes `VERIFIED` only when its slice module `tests/slices/test_<REQ_ID>.py` exists and passes in CI (`TESTING_AND_QA_STRATEGY.md` §4). For rows showing `—`, that file is the target.
- **Release** is `FD-V1` / `FD-V2`. Nothing here is FD-V3; V3 items stay deferred (Master Prompt §15).

### Status summary (224 requirements)

| Status | Count |
|---|---|
| NOT_IMPL | 180 |
| PARTIAL | 23 |
| VERIFIED (deterministic/mocked, local) | 6 |
| DEFECT | 5 |
| BROKEN (G-04 WIP) | 4 |
| MOCKED | 1 |
| SCAFFOLD | 1 |
| n/a (migration/policy) | 4 |

## 2. Target design per area

Where each column's target lives. Final route and column names are owned by `API_AND_EVENT_CONTRACTS.md` and `DATABASE_DESIGN_AND_ERD.md`; routes marked "per API doc" are summarised here.

| Area | Screens (IA) | Target API (API_AND_EVENT_CONTRACTS) | Target service | Target workflow | Target DB (DATABASE_DESIGN_AND_ERD) | Target audit / version |
|---|---|---|---|---|---|---|
| PRJ | S-PRJ-01, S-PRJ-02 | `POST/GET /projects`, `PATCH /projects/{pid}`, `POST /projects/{pid}/archive` | `ProjectService` | — | `projects` (ext: production_mode, template) | `project_created`/`project_updated` + project_versions |
| FMT | S-PRJ-02 | `PATCH /projects/{pid}` | `ProjectService` (format templates) | — | `projects` (template JSONB) | `project_updated` |
| IAM | S-TEAM-01, S-TEAM-02 | `GET /me`, `POST/PATCH /org/members`, `PUT /projects/{pid}/members/{user_id}` | `AuthProvider`, `AuthzService.require` | — | `memberships`, `project_memberships`, `role_templates`, `capabilities`, `users` (ext) | `membership_changed` |
| AST | S-AST-01..03 | `POST /projects/{pid}/assets/upload`, `POST /projects/{pid}/uploads`, `GET /assets/{id}/download` | `AssetService`, `StorageService` | media pool tasks | `assets` (ext), `asset_derivatives`, `asset_lineage` | `asset_uploaded` |
| SCR | S-SCR-01..04 | `/projects/{pid}/screenplay-versions`, `/screenplay-versions/{id}/submit|lock`, `/screenplay-suggestions` | `ScreenplayService` | WF-01 input | `screenplay_versions`, `screenplay_changes`, `screenplay_suggestions`, `impact_analyses` | `screenplay_locked`/`revision_*` + version |
| STY | S-BRN-01, S-BRN-02, S-SCR-02 | `POST /projects/{pid}/workflows/script-intelligence`, `GET /scenes`, `/entities` | `ScriptIntelligenceService`, `ScriptReviewService` | WF-01 | `scenes` (ext), `dialogue_segments`, `timeline_events` | `script_intelligence_committed` + project_versions |
| RES | S-RES-01..05 | `/projects/{pid}/research/*`, `POST .../workflows/historical-research` | `ResearchService`, `HistoricalResearchService`, `ResearchReviewService` | WF-02 | `research_*`, `timeline_events` | `research_committed` + project_versions |
| CHR | S-CHR-01, S-CHR-02 | `POST /projects/{pid}/characters` | `CharacterService` | WF-05 | `characters`, `character_versions`, `character_identity_profiles`, `character_states` | `character_version_approved` |
| PHY | S-PHY-01 | `/characters/{id}/measurements` (per API doc) | `PhysicalIdentityService` | WF-05 | `physical_identity_profiles`, `body_measurements` | `measurement_recorded`/`verified` |
| CNS | S-DH-01 (consent panel) | `POST /performers`, `/performers/{id}/consents`, `/consents/{id}/verify|revoke`, `/consent-checks` | `ConsentService`, `ConsentPolicy.check` | — (gate in WF-09/10) | `performers`, `performer_consents` | `consent_recorded`/`revoked` (approval_level=consent) |
| DH | S-DH-01, S-DH-02 | `POST /projects/{pid}/digital-humans` | `DigitalHumanService` + `ConsentPolicy` | WF-05, WF-10 | `digital_humans`, `avatar_versions` | `avatar_version_approved` |
| CST | S-CST-01 | `/projects/{pid}/costumes` (per API doc) | `WorldService` | WF-05 | `costumes`, `costume_states` | `costume_approved` |
| PRP | S-CST-02 | `/projects/{pid}/props` (per API doc) | `WorldService` | WF-05 | `props`, `prop_states` | `prop_approved` |
| ENV | S-ENV-01 | `/projects/{pid}/locations` (per API doc) | `WorldService` | WF-05 | `locations`, `environment_profiles`, `environment_states` | `location_approved` |
| SB | S-SB-01, S-SB-02 | `POST .../workflows/storyboard-intelligence`, `GET .../storyboard/panels` | `StoryboardIntelligenceService`, `StoryboardReviewService` | WF-03 | `storyboard_panels` (+candidates) | `storyboard_committed` + project_versions |
| CIN | S-CIN-01, S-BIB-01, S-BIB-02 | `PATCH /shots/{id}` (camera_spec), `/projects/{pid}/film-bible/*` | `CinematographyService`, `FilmBibleService` | WF-04, WF-06 | `cinematography_profiles`, `camera_profiles`, `lens_profiles`, `lighting_profiles`, `shots.camera_spec`, `film_bible_rules` | `visual_rule_*`, `film_bible_committed` |
| SEQ | S-SEQ-01, S-SEQ-02 | `POST /projects/{pid}/sequences` | `ShotPlanningService` | WF-06 | `sequences` | `sequence_approved` |
| SHT | S-SHT-01, S-MTH-01 | `POST /sequences/{id}/shots`, `GET/PATCH /shots/{id}` | `ShotPlanningService` | WF-06 | `shots` | `shot_spec_approved` + version |
| CON | S-CON-01..03 | `/projects/{pid}/continuity/*`, `POST /continuity/findings/{id}/decisions`, `GET /impact-analyses/{id}` | `ContinuityService` | WF-07 | `continuity_rules`, `continuity_findings`, `continuity_decisions`, `impact_analyses` | `continuity_decision_recorded` |
| CTX | S-AID-01 (context drawer) | internal (no public write route) | `ContextResolver` | consumed by WF-05..11 | `context_packages` | package hash on `ai_runs` |
| AID | S-AID-01 | `POST /projects/{pid}/workflow-runs` | `ModelGateway`, `AIDirectorService` | WF-08 | `ai_runs`, `prompt_versions`, `evaluation_records` | `ai_run_completed` |
| PKG | S-PKG-01..03 | `POST /shots/{id}/packages`, `GET /packages/{id}`, `POST /packages/{id}/exports` | `PackageService`, `PromptCompiler` | WF-09 | `production_packages`, `prompt_versions` | `package_compiled`/`exported` |
| INT | S-REG-01, S-REG-02, S-PKG-03, S-EXE-01 | `GET /providers`, `POST /org/provider-connections`, `POST /packages/{id}/generation-jobs`, `POST /webhooks/providers/...` | `ProviderRegistryService`, `ProviderAdapter` | WF-10 | `providers`, `provider_capability_snapshots`, `provider_connections` | `provider_submit`, `package_exported` |
| GEN | S-EXE-01, S-EXE-02 | `/generation-jobs/{id}/cancel|reconcile|convert-to-manual` | `GenerationJobService` | WF-10 | `generation_jobs`, `generation_attempts`, `generation_cost_records`, `usage_records` | `generation_submitted`/`charged` (approval_level=cost) |
| HYB | S-CAP-01, S-CAP-02 | `/shots/{id}` capture plan, `POST /projects/{pid}/uploads` | `CapturePlanService` | WF-06, WF-11 | `capture_plans`, `capture_requirements`, `capture_manifests`, `production_footage` | `capture_manifest_approved` |
| OUT | S-OUT-01, S-EXE-02 | `POST /packages/{id}/imports`, `/imports/{id}/complete|mapping|reviews`, `POST /output-reviews/{id}/revision-requests` | `ImportService`, `OutputReviewService` | WF-11 | `import_jobs`, `output_reviews`, `revision_requests`, `asset_lineage` | `output_reviewed` + version |
| LIB | S-LIB-01, S-LIB-02 | `GET /projects/{pid}/assets`, `GET /assets/{id}/lineage` | `LibraryService` | — | `assets`, `asset_lineage` | read-only |
| VOC | S-VOC-01, S-VOC-02 | `/projects/{pid}/voice-profiles` (per API doc) | `VoiceService` + `ConsentPolicy` | WF-10 | `voice_profiles`, `dialogue_segments` | `voice_profile_approved` |
| POST | S-PST-01 | `POST /projects/{pid}/handoff-manifests`, `GET /exports/{id}` | `HandoffService` | — | export manifest (DB design) | `handoff_exported` |
| APR | S-APR-01..03 | `POST /approvals/{id}/decide`, `GET /me/approvals` | per-workflow `decide()` → `ApprovalService` | all WF interrupt gates | `approval_requests` (generalised) | `approval_decided` |
| VER | S-APR-02 | `GET /projects/{pid}/versions` | `VersioningService` | all WF commits | `project_versions` + artifact `*_versions` | project_versions row |
| AUD | S-APR-03 | `GET /projects/{pid}/audit-log` | `AuditRepository.record` | all | `audit_events` (append-only) | is the audit |
| OPS | S-OPS-01 | `GET /workflow-runs/{id}`, `POST /workflow-runs/{id}/cancel`, `/health`, `/ready` | worker, outbox | all | `outbox_tasks` (ext), `workflow_runs`, `notifications`, `idempotency_keys` | — |
## 3. Master Prompt §15 coverage check (55 items)

Every V1 and V2 item maps to at least one requirement ID. The mapping is taken from PRD v1.0 §13 (release scope).

| §15 item | Title | Requirement IDs |
|---|---|---|
| V1-01 | Project management | TFD-PRJ-001, TFD-PRJ-002, TFD-PRJ-003, TFD-PRJ-004, TFD-PRJ-005, TFD-PRJ-006, TFD-PRJ-007, TFD-FMT-001, TFD-FMT-002, TFD-FMT-003, TFD-FMT-004 |
| V1-02 | Team access and role model | TFD-IAM-001, TFD-IAM-002, TFD-IAM-003, TFD-IAM-004, TFD-IAM-005, TFD-IAM-006, TFD-IAM-007, TFD-IAM-008, TFD-IAM-009 |
| V1-03 | Universal asset ingestion | TFD-AST-001, TFD-AST-002, TFD-AST-003, TFD-AST-004, TFD-AST-005, TFD-AST-006, TFD-AST-007, TFD-AST-008, TFD-AST-009, TFD-AST-010 |
| V1-04 | Script intelligence | TFD-STY-001, TFD-STY-002, TFD-STY-003, TFD-STY-007, TFD-SCR-001 |
| V1-05 | Locked screenplay governance | TFD-SCR-002, TFD-SCR-003, TFD-SCR-004, TFD-SCR-006, TFD-SCR-007, TFD-SCR-008, TFD-SCR-009, TFD-SCR-010, TFD-SCR-011 |
| V1-06 | AI suggestions workspace | TFD-SCR-005 |
| V1-07 | Historical research | TFD-RES-001, TFD-RES-002, TFD-RES-003, TFD-RES-004, TFD-RES-005, TFD-RES-010 |
| V1-08 | Historical timeline | TFD-RES-006 |
| V1-09 | Film Bible | TFD-CIN-010, TFD-CIN-011, TFD-CIN-012, TFD-CIN-013 |
| V1-10 | Character Bible | TFD-CHR-001, TFD-CHR-002, TFD-CHR-003, TFD-CHR-004, TFD-CHR-005, TFD-CHR-006, TFD-CHR-007, TFD-CHR-008, TFD-CHR-009 |
| V1-11 | Physical Identity Profile | TFD-PHY-001, TFD-PHY-002, TFD-PHY-003, TFD-PHY-004, TFD-PHY-006 |
| V1-12 | Costume Bible | TFD-CST-001, TFD-CST-002, TFD-CST-003 |
| V1-13 | Props and weapons register | TFD-PRP-001, TFD-PRP-002, TFD-PRP-003 |
| V1-14 | Environment and location Bible | TFD-ENV-001, TFD-ENV-002, TFD-ENV-003, TFD-ENV-004 |
| V1-15 | Storyboard intelligence | TFD-SB-001, TFD-SB-002, TFD-SB-003, TFD-SB-004 |
| V1-16 | Cinematography Bible | TFD-CIN-005, TFD-CIN-006 |
| V1-17 | Camera/lens planning | TFD-CIN-001, TFD-CIN-002, TFD-CIN-003, TFD-CIN-004 |
| V1-18 | Sequence planning | TFD-SEQ-001, TFD-SEQ-002 |
| V1-19 | Shot planning | TFD-SHT-001, TFD-SHT-002, TFD-SHT-004, TFD-SHT-005, TFD-SHT-006 |
| V1-20 | Continuity management | TFD-CON-001, TFD-CON-002, TFD-CON-003, TFD-CON-004, TFD-CON-005, TFD-CON-006, TFD-CON-008 |
| V1-21 | Context Resolver | TFD-CTX-001, TFD-CTX-002, TFD-CTX-003, TFD-CTX-004 |
| V1-22 | AI Director review | TFD-AID-001, TFD-AID-002, TFD-AID-003, TFD-AID-004, TFD-AID-005, TFD-AID-006, TFD-AID-007 |
| V1-23 | Provider-neutral Shot Specification | TFD-SHT-003 |
| V1-24 | Prompt compiler | TFD-PKG-001, TFD-PKG-003, TFD-PKG-005, TFD-PKG-006 |
| V1-25 | Production package generation | TFD-PKG-002, TFD-PKG-004, TFD-PKG-007 |
| V1-26 | Manual export and copy | TFD-INT-001, TFD-INT-003, TFD-INT-004, TFD-INT-006 |
| V1-27 | Manual asset import | TFD-OUT-001, TFD-OUT-002, TFD-OUT-004, TFD-OUT-005, TFD-OUT-006 |
| V1-28 | Review and approval | TFD-APR-001, TFD-APR-002, TFD-APR-003, TFD-APR-004, TFD-APR-005, TFD-APR-006, TFD-APR-007 |
| V1-29 | Versions and audit | TFD-VER-001, TFD-VER-002, TFD-VER-003, TFD-VER-004, TFD-VER-005, TFD-AUD-001, TFD-AUD-002, TFD-AUD-003, TFD-AUD-004 |
| V1-30 | Core operational observability | TFD-OPS-001, TFD-OPS-002, TFD-OPS-003, TFD-OPS-004, TFD-OPS-005, TFD-OPS-006, TFD-OPS-007, TFD-OPS-008, TFD-OPS-009, TFD-OPS-010 |
| V2-01 | Connected image generation where verified | TFD-INT-002, TFD-GEN-005 |
| V2-02 | Manual image generation workflows | TFD-GEN-008 |
| V2-03 | Character reference generation | TFD-GEN-005 |
| V2-04 | Environment reference production | TFD-GEN-010 |
| V2-05 | Costume and prop reference production | TFD-GEN-011 |
| V2-06 | Keyframe workflows | TFD-GEN-006 |
| V2-07 | Performance-preserving transformation | TFD-DH-004 |
| V2-08 | Digital human workflows | TFD-DH-001, TFD-DH-002, TFD-DH-003, TFD-DH-005, TFD-DH-006, TFD-DH-009 |
| V2-09 | AI anchor workflows | TFD-DH-007 |
| V2-10 | Motion capture integration/handoff | TFD-DH-008 |
| V2-11 | Body measurement integration/handoff | TFD-PHY-005, TFD-PHY-007 |
| V2-12 | Chroma and live-action production workflows | TFD-HYB-001, TFD-HYB-002, TFD-HYB-003, TFD-HYB-004, TFD-HYB-005 |
| V2-13 | Video generation through verified adapters | TFD-GEN-007, TFD-INT-002 |
| V2-14 | Voice workflows | TFD-VOC-001, TFD-VOC-002, TFD-VOC-003, TFD-VOC-004 |
| V2-15 | Multilingual dubbing | TFD-VOC-005, TFD-VOC-007 |
| V2-16 | Lip-sync integration | TFD-VOC-006 |
| V2-17 | Generation job tracking | TFD-GEN-001, TFD-GEN-009 |
| V2-18 | Generation attempt tracking | TFD-GEN-002, TFD-GEN-003 |
| V2-19 | Provider capability registry | TFD-INT-003, TFD-INT-005, TFD-INT-007, TFD-INT-008, TFD-INT-009, TFD-INT-010 |
| V2-20 | Cost and credit tracking | TFD-GEN-004 |
| V2-21 | Output import and inspection | TFD-OUT-002, TFD-OUT-003 |
| V2-22 | Continuity comparison | TFD-CON-007 |
| V2-23 | Revision and regeneration requests | TFD-OUT-005 |
| V2-24 | Shot-level production library | TFD-LIB-001, TFD-LIB-002, TFD-LIB-003 |
| V2-25 | Production handoff package | TFD-POST-001, TFD-POST-002, TFD-POST-003 |

## 4. Matrix

### PRJ — Project

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-PRJ-001** | Create a project with a stable ID, title, logline, genre, production format… | Producer: set up and steer the project | §13-S1 | `apps/ui/app.py` (new-project form) | `apps/api/routers/projects.py` POST/GET `/projects`, GET `/projects/{id}` | `packages/services/projects.py::ProjectService` | Project, ProductionMode | — | `projects`, `project_versions` | `AuditAction.PROJECT_CREATED` | `tests/api/test_tenant_isolation_api.py`, `tests/api/test_script_intelligence_slice.py` | FD-V1 | PARTIAL (title/logline/genre only, `routers/projects.py`) | V1-01, FD-FR-001/002 |
| **TFD-PRJ-002** | List, get, update metadata and archive projects, scoped to the caller's project… | Producer: set up and steer the project | §13-S1 | `apps/ui/app.py` (new-project form) | `apps/api/routers/projects.py` POST/GET `/projects`, GET `/projects/{id}` | `packages/services/projects.py::ProjectService` | Project, ProductionMode | — | `projects`, `project_versions` | `AuditAction.PROJECT_CREATED` | `tests/api/test_tenant_isolation_api.py`, `tests/api/test_script_intelligence_slice.py` | FD-V1 | PARTIAL (no update/archive) | V1-01, FD-FR-001 |
| **TFD-PRJ-003** | Project-level `production_mode ∈ {fully_ai, hybrid_live_action, mixed}`.… | Producer: set up and steer the project | §13-S1 | — | — | — | Project, ProductionMode | — | — | — | — | FD-V1 | NOT_IMPL | V1-01 |
| **TFD-PRJ-004** | Nullable mode override at sequence, scene, character and shot. Effective mode… | Producer: set up and steer the project | §13-S1 | — | — | — | Project, ProductionMode | — | — | — | — | FD-V1 | NOT_IMPL | V1-01 |
| **TFD-PRJ-005** | Mode conflict detection: a shot whose production method is outside the allowed… | Producer: set up and steer the project | §13-S1 | — | — | — | Project, ProductionMode | — | — | — | — | FD-V1 | NOT_IMPL | V1-01 |
| **TFD-PRJ-006** | Changing mode at project, sequence, scene or character level runs an impact… | Producer: set up and steer the project | §13-S1 | — | — | — | Project, ProductionMode | — | — | — | — | FD-V1 | NOT_IMPL | V1-01 |
| **TFD-PRJ-007** | Project Overview shows the canonical screenplay version, project version, mode… | Producer: set up and steer the project | §13-S1 | `apps/ui/views/overview.py` | — | — | Project, ProductionMode | — | — | — | — | FD-V1 | PARTIAL (`apps/ui/views/overview.py` counts only) | V1-01, UX-FD-02 |

### FMT — Formats

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-FMT-001** | Template catalogue for all 13 formats in §8. Each template defines structure… | Producer: pick a format and output profile | §13-S1 | — | — | — | FormatTemplate, OutputProfile | — | — | — | — | FD-V1 | NOT_IMPL | V1-01 |
| **TFD-FMT-002** | Output profiles (resolution, aspect ratio, fps, duration target, audio,… | Producer: pick a format and output profile | §13-S1 | — | — | — | FormatTemplate, OutputProfile | — | — | — | — | FD-V1 | NOT_IMPL | V1-01 |
| **TFD-FMT-003** | Episodic structure for OTT series and episodic historical series: series →… | Producer: pick a format and output profile | §13-S1 | — | — | — | FormatTemplate, OutputProfile | — | — | — | — | FD-V1 | NOT_IMPL | V1-01 |
| **TFD-FMT-004** | Format-specific workflow variants (documentary footage-first with optional… | Producer: pick a format and output profile | §13-S1 | — | — | — | FormatTemplate, OutputProfile | — | — | — | — | FD-V1 | NOT_IMPL | V1-01 |
| **TFD-FMT-005** | Changing a template after creation shows an impact review before applying | Producer: pick a format and output profile | §13-S1 | — | — | — | FormatTemplate, OutputProfile | — | — | — | — | FD-V1 | NOT_IMPL | — |

### IAM — Identity & access

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-IAM-001** | Authenticated identity (OIDC/JWT behind an `AuthProvider` port). `X-Actor-ID`… | Admin: control who can do what | cross-cutting | — | `apps/api/dependencies.py::get_actor` (X-Actor-ID only) | `packages/services/identity.py::IdentityService.resolve` | Membership, Capability | — | `users` | — | — | FD-V1 | NOT_IMPL (SEC-01/02) — **gate DEC-002** | V1-02, FD-FR-043 |
| **TFD-IAM-002** | Organisation `memberships` with role. `users.role` is migrated into a… | Admin: control who can do what | cross-cutting | — | — | — | Membership, Capability | — | — | — | — | FD-V1 | NOT_IMPL | V1-02, FD-FR-001 |
| **TFD-IAM-003** | `project_memberships` with project role. Users see and act only on projects… | Admin: control who can do what | cross-cutting | — | — | — | Membership, Capability | — | — | — | — | FD-V1 | NOT_IMPL | V1-02, FD-FR-043 |
| **TFD-IAM-004** | Capability matrix (`role_templates` → `capabilities`), deny-by-default,… | Admin: control who can do what | cross-cutting | — | — | — | Membership, Capability | — | — | — | — | FD-V1 | NOT_IMPL — **OPEN DEC-027** | V1-02, FD-FR-043 |
| **TFD-IAM-005** | `screenplay.approve_lock` (management authority) is a distinct capability. The… | Admin: control who can do what | cross-cutting | — | — | — | Membership, Capability | — | — | — | — | FD-V1 | NOT_IMPL | V1-02 |
| **TFD-IAM-006** | `cost.approve` capability and per-project budget caps for provider spend | Admin: control who can do what | cross-cutting | — | — | — | Membership, Capability | — | — | — | — | FD-V2 | NOT_IMPL | V1-02, FD-FR-038 |
| **TFD-IAM-007** | Asset-level permission: performer face, body and voice references and consent… | Admin: control who can do what | cross-cutting | — | — | — | Membership, Capability | — | — | — | — | FD-V1 | NOT_IMPL | V1-02 |
| **TFD-IAM-008** | Membership or capability revocation takes effect on the next request. Pending… | Admin: control who can do what | cross-cutting | — | — | — | Membership, Capability | — | — | — | — | FD-V1 | NOT_IMPL | V1-02 |
| **TFD-IAM-009** | Tenant and project isolation: every repository getter is scoped, and foreign… | Admin: control who can do what | cross-cutting | — | — | `ProjectRepository/ApprovalRepository/WorkflowRunRepository.get_scoped` | Membership, Capability | — | — | — | `tests/api/test_tenant_isolation_api.py` | FD-V1 | PARTIAL (projects/approvals/runs scoped; `ResearchRepository.get_question/get_source`, `FilmBibleRepository.get_rule` unscoped — SEC-04) | V1-02, FD-FR-043 |

### AST — Assets

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-AST-001** | Multi-file upload streamed to private object storage. Per-file size limits. The… | Crew: ingest and find source material | §13-S2 | `apps/ui/views/assets.py` | `apps/api/routers/assets.py` POST `/projects/{pid}/assets/upload`, GET list | `packages/services/assets.py::AssetService`; `packages/storage/service.py::LocalFileSystemStorageService` | Asset, AssetDerivative | — | `assets` | `AuditAction.ASSET_UPLOADED` | `tests/api/test_assets_api.py`, `tests/integration/test_storage_service.py` | FD-V1 | PARTIAL (`routers/assets.py:27` buffers whole file; PERF-03) — **gate DEC-003** | V1-03, FD-FR-003 |
| **TFD-AST-002** | File-signature (magic-byte) validation; client MIME is not trusted. Processing… | Crew: ingest and find source material | §13-S2 | — | — | — | Asset, AssetDerivative | — | — | — | — | FD-V1 | NOT_IMPL (SEC-05) | V1-03, FD-FR-004 |
| **TFD-AST-003** | Category taxonomy covering screenplay, storyboard, character reference, face… | Crew: ingest and find source material | §13-S2 | `apps/ui/views/assets.py` | `apps/api/routers/assets.py` POST `/projects/{pid}/assets/upload`, GET list | `packages/services/assets.py::AssetService`; `packages/storage/service.py::LocalFileSystemStorageService` | Asset, AssetDerivative | — | `assets` | `AuditAction.ASSET_UPLOADED` | `tests/api/test_assets_api.py`, `tests/integration/test_storage_service.py` | FD-V1 | PARTIAL (`AssetType` 6 values; upload hard-codes `script`) | V1-03, FD-FR-003/006 |
| **TFD-AST-004** | Immutable original with checksum, uploader, timestamp, source and rights… | Crew: ingest and find source material | §13-S2 | `apps/ui/views/assets.py` | `apps/api/routers/assets.py` POST `/projects/{pid}/assets/upload`, GET list | `packages/services/assets.py::AssetService`; `packages/storage/service.py::LocalFileSystemStorageService` | Asset, AssetDerivative | — | `assets` | `AuditAction.ASSET_UPLOADED` | `tests/api/test_assets_api.py`, `tests/integration/test_storage_service.py` | FD-V1 | PARTIAL (content-addressed `LocalFileSystemStorageService`) | V1-03, FD-FR-004 |
| **TFD-AST-005** | Per-asset processing state with partial-failure isolation. One bad file never… | Crew: ingest and find source material | §13-S2 | — | — | — | Asset, AssetDerivative | — | — | — | — | FD-V1 | NOT_IMPL | V1-03, FD-FR-005 |
| **TFD-AST-006** | Text derivatives for screenplay and document formats (Fountain, FDX, PDF text… | Crew: ingest and find source material | §13-S2 | — | — | `packages/services/script_review.py` (UTF-8 decode, defect) | Asset, AssetDerivative | — | — | — | — | FD-V1 | BROKEN for PDF/DOCX (`script_review.py` decodes as UTF-8) | V1-03, FD-FR-007/008 |
| **TFD-AST-007** | Media derivatives (thumbnails, video proxies, audio waveform, sampled frames,… | Crew: ingest and find source material | §13-S2 | — | — | — | Asset, AssetDerivative | — | — | — | — | FD-V1/V2 | NOT_IMPL | V1-03, FD-FR-008 |
| **TFD-AST-008** | Duplicate and near-duplicate detection that never deletes originals | Crew: ingest and find source material | §13-S2 | — | — | — | Asset, AssetDerivative | — | — | — | — | FD-V1 | NOT_IMPL | V1-03, FD-FR-009 |
| **TFD-AST-009** | Reference-video analysis (timecodes, shot boundaries, camera, motion and… | Crew: ingest and find source material | §13-S2 | — | — | — | Asset, AssetDerivative | — | — | — | — | FD-V1 | NOT_IMPL | V1-03, FD-FR-023/024 |
| **TFD-AST-010** | Signed, short-lived download URLs only. No public asset URL. Downloads are… | Crew: ingest and find source material | §13-S2 | — | — | — | Asset, AssetDerivative | — | — | — | — | FD-V1 | NOT_IMPL | V1-03, FD-FR-004 |

### SCR — Screenplay governance

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-SCR-001** | Screenplay import (Fountain, FDX, PDF, DOCX, TXT) creates a… | Management/Director: govern the locked screenplay | §13-S2 | — | `apps/api/routers/assets.py` upload (script = asset) | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | `packages/workflows/script_intelligence/` reads asset bytes | — | — | — | FD-V1 | PARTIAL (asset only) | V1-04, FD-FR-020 |
| **TFD-SCR-002** | Approved screenplay lock: management approval (`approval_level=management`)… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-05 |
| **TFD-SCR-003** | Locked versions are immutable. Any attempt to mutate text, scenes or dialogue… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-05 |
| **TFD-SCR-004** | AI analysis (WF-01 and successors) reads only from a specific… | Management/Director: govern the locked screenplay | §13-S2 | — | `apps/api/routers/assets.py` upload (script = asset) | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | `packages/workflows/script_intelligence/` reads asset bytes | — | — | — | FD-V1 | PARTIAL (WF-01 reads asset bytes) | V1-05 |
| **TFD-SCR-005** | AI Suggestions Workspace: suggestions in seven kinds (alternative scene,… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-06 |
| **TFD-SCR-006** | Director revision: create a draft derived from the canonical version, edit it… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-05 |
| **TFD-SCR-007** | Management review of a revision: approve, reject or request changes, with… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-05 |
| **TFD-SCR-008** | Full history retained: original, all revisions, suggestions with dispositions,… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-05 |
| **TFD-SCR-009** | Scenes, dialogue segments, sequences, shots, packages and localised scripts… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-05 |
| **TFD-SCR-010** | When a revision is approved, compute an `impact_analysis` (affected scenes,… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-05, FD-FR-030 |
| **TFD-SCR-011** | Per-episode screenplay governance for episodic formats (see FMT-003) | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V1 | NOT_IMPL | V1-05 |
| **TFD-SCR-012** | In-app rich screenplay editor with redline. Depends on the frontend decision… | Management/Director: govern the locked screenplay | §13-S2 | — | — | — | ScreenplayVersion, ScreenplayChange, ScreenplaySuggestion | — | — | — | — | FD-V2 | NOT_IMPL — **OPEN DEC-009** | — |

### STY — Story intelligence

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-STY-001** | Scene extraction from a screenplay version with page/line locators → candidates… | Director: understand the story | §13-S3 | `apps/ui/views/script_intelligence.py`, `views/review.py` | `apps/api/routers/workflows.py` POST `.../workflows/script-intelligence`; `apps/api/routers/projects.py` GET `/scenes`, `/entities` | `packages/services/script_intelligence.py`, `packages/services/script_review.py` | Scene, DialogueSegment | WF-01 `packages/workflows/script_intelligence/graph.py`, `parser.py::ScreenplayParser` | `scenes`, `entities`, `scene_candidates`, `entity_candidates` | `SCRIPT_INTELLIGENCE_COMMITTED/REJECTED` + `project_versions` | `tests/api/test_script_intelligence_slice.py`, `tests/workflows/test_graph_recovery.py` | FD-V1 | VERIFIED (deterministic; `ScreenplayParser`) | V1-04, FD-FR-020, G-01/WF-01 |
| **TFD-STY-002** | Dialogue segments extracted verbatim (speaker, line, parenthetical, scene,… | Director: understand the story | §13-S3 | — | — | — | Scene, DialogueSegment | — | — | — | — | FD-V1 | NOT_IMPL | V1-04, FD-FR-020, G-01/WF-01 |
| **TFD-STY-003** | Character, location and time-of-day extraction resolved into… | Director: understand the story | §13-S3 | `apps/ui/views/script_intelligence.py`, `views/review.py` | `apps/api/routers/workflows.py` POST `.../workflows/script-intelligence`; `apps/api/routers/projects.py` GET `/scenes`, `/entities` | `packages/services/script_intelligence.py`, `packages/services/script_review.py` | Scene, DialogueSegment | WF-01 `packages/workflows/script_intelligence/graph.py`, `parser.py::ScreenplayParser` | `scenes`, `entities`, `scene_candidates`, `entity_candidates` | `SCRIPT_INTELLIGENCE_COMMITTED/REJECTED` + `project_versions` | `tests/api/test_script_intelligence_slice.py`, `tests/workflows/test_graph_recovery.py` | FD-V1 | PARTIAL (`entities`) | V1-04, FD-FR-025, G-01/WF-01 |
| **TFD-STY-004** | Story Brain epistemic states (known, unknown, ambiguous, assumed, conflicting,… | Director: understand the story | §13-S3 | — | — | — | Scene, DialogueSegment | — | — | — | — | FD-V1 | NOT_IMPL | FD-FR-010, G-01/WF-01 |
| **TFD-STY-005** | Story/narrative timeline, distinct from and linked to the historical timeline | Director: understand the story | §13-S3 | — | — | — | Scene, DialogueSegment | — | — | — | — | FD-V1 | NOT_IMPL | FD-FR-018, G-01/WF-01 |
| **TFD-STY-006** | Character relationships | Director: understand the story | §13-S3 | — | — | — | Scene, DialogueSegment | — | — | — | — | FD-V1 | NOT_IMPL | G-01/WF-01 |
| **TFD-STY-007** | Golden screenplay set (including non-uppercase cues, PDF, FDX) with… | Director: understand the story | §13-S3 | — | — | — | Scene, DialogueSegment | — | — | — | — | FD-V1 | NOT_IMPL | V1-04, FD-FR-049, G-01/WF-01 |

### RES — Historical research

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-RES-001** | Research questions with status (`open/investigating/resolved/deferred`) and the… | Researcher: ground the world in evidence | §13-S4 | `apps/ui/views/historical_research.py` | `apps/api/routers/research.py` GET/POST `/questions`, `/sources`; GET `/claims`, `/conflicts`; `apps/api/routers/workflows.py` historical-research | `packages/services/research.py::ResearchService`, `packages/services/historical_research.py`, `packages/services/research_review.py` | ResearchQuestion, Source, Claim, Conflict | WF-02 `packages/workflows/historical_research/graph.py`, `investigator.py` (mock) | `research_questions/sources/claims/conflicts` + `research_*_candidates` | `RESEARCH_*` actions + `project_versions` (unlocked bump, PERF-06) | `tests/api/test_historical_research_api.py` | FD-V1 | VERIFIED (mocked) | V1-07, FD-FR-015, G-02/WF-02 |
| **TFD-RES-002** | Source registry with tier (`tier_0_project…tier_3_discovery`), locator,… | Researcher: ground the world in evidence | §13-S4 | `apps/ui/views/historical_research.py` | `apps/api/routers/research.py` GET/POST `/questions`, `/sources`; GET `/claims`, `/conflicts`; `apps/api/routers/workflows.py` historical-research | `packages/services/research.py::ResearchService`, `packages/services/historical_research.py`, `packages/services/research_review.py` | ResearchQuestion, Source, Claim, Conflict | WF-02 `packages/workflows/historical_research/graph.py`, `investigator.py` (mock) | `research_questions/sources/claims/conflicts` + `research_*_candidates` | `RESEARCH_*` actions + `project_versions` (unlocked bump, PERF-06) | `tests/api/test_historical_research_api.py` | FD-V1 | PARTIAL (locators thin) | V1-07, FD-FR-013, G-02/WF-02 |
| **TFD-RES-003** | Typed claims (`historical_fact, historical_interpretation, contested_claim,… | Researcher: ground the world in evidence | §13-S4 | `apps/ui/views/historical_research.py` | `apps/api/routers/research.py` GET/POST `/questions`, `/sources`; GET `/claims`, `/conflicts`; `apps/api/routers/workflows.py` historical-research | `packages/services/research.py::ResearchService`, `packages/services/historical_research.py`, `packages/services/research_review.py` | ResearchQuestion, Source, Claim, Conflict | WF-02 `packages/workflows/historical_research/graph.py`, `investigator.py` (mock) | `research_questions/sources/claims/conflicts` + `research_*_candidates` | `RESEARCH_*` actions + `project_versions` (unlocked bump, PERF-06) | `tests/api/test_historical_research_api.py` | FD-V1 | VERIFIED (`ClaimClass`) | V1-07, FD-FR-012, G-02/WF-02 |
| **TFD-RES-004** | Conflicts stay visible; an unsupported claim can never be marked… | Researcher: ground the world in evidence | §13-S4 | `apps/ui/views/historical_research.py` | `apps/api/routers/research.py` GET/POST `/questions`, `/sources`; GET `/claims`, `/conflicts`; `apps/api/routers/workflows.py` historical-research | `packages/services/research.py::ResearchService`, `packages/services/historical_research.py`, `packages/services/research_review.py` | ResearchQuestion, Source, Claim, Conflict | WF-02 `packages/workflows/historical_research/graph.py`, `investigator.py` (mock) | `research_questions/sources/claims/conflicts` + `research_*_candidates` | `RESEARCH_*` actions + `project_versions` (unlocked bump, PERF-06) | `tests/api/test_historical_research_api.py` | FD-V1 | PARTIAL | V1-07, FD-FR-014, G-02/WF-02 |
| **TFD-RES-005** | Manual research writes go through candidate → approval, or a role-gated… | Researcher: ground the world in evidence | §13-S4 | `apps/ui/views/historical_research.py` | `apps/api/routers/research.py` GET/POST `/questions`, `/sources`; GET `/claims`, `/conflicts`; `apps/api/routers/workflows.py` historical-research | `packages/services/research.py::ResearchService`, `packages/services/historical_research.py`, `packages/services/research_review.py` | ResearchQuestion, Source, Claim, Conflict | WF-02 `packages/workflows/historical_research/graph.py`, `investigator.py` (mock) | `research_questions/sources/claims/conflicts` + `research_*_candidates` | `RESEARCH_*` actions + `project_versions` (unlocked bump, PERF-06) | `tests/api/test_historical_research_api.py` | FD-V1 | NOT_IMPL (SEC-06, `ResearchService.create_*`) | V1-07, G-02/WF-02 |
| **TFD-RES-006** | Historical timeline events with uncertain dates (original expression,… | Researcher: ground the world in evidence | §13-S4 | — | — | — | ResearchQuestion, Source, Claim, Conflict | — | — | — | — | FD-V1 | NOT_IMPL | V1-08, FD-FR-018/019, G-02/WF-02 |
| **TFD-RES-007** | Historical brief / period resolution (date range, region, polity, event,… | Researcher: ground the world in evidence | §13-S4 | — | — | — | ResearchQuestion, Source, Claim, Conflict | — | — | — | — | FD-V1 | NOT_IMPL | FD-FR-011, G-02/WF-02 |
| **TFD-RES-008** | Temporal visual profile (clothing, grooming, weapons, architecture, materials… | Researcher: ground the world in evidence | §13-S4 | — | — | — | ResearchQuestion, Source, Claim, Conflict | — | — | — | — | FD-V1 | NOT_IMPL | FD-FR-016, G-02/WF-02 |
| **TFD-RES-009** | Anachronism flags with evidence and alternatives | Researcher: ground the world in evidence | §13-S4 | — | — | — | ResearchQuestion, Source, Claim, Conflict | — | — | — | — | FD-V1 | NOT_IMPL | FD-FR-017, G-02/WF-02 |
| **TFD-RES-010** | Investigator runs behind the ModelGateway with real retrieval when DEC-004 is… | Researcher: ground the world in evidence | §13-S4 | `apps/ui/views/historical_research.py` | `apps/api/routers/research.py` GET/POST `/questions`, `/sources`; GET `/claims`, `/conflicts`; `apps/api/routers/workflows.py` historical-research | `packages/services/research.py::ResearchService`, `packages/services/historical_research.py`, `packages/services/research_review.py` | ResearchQuestion, Source, Claim, Conflict | WF-02 `packages/workflows/historical_research/graph.py`, `investigator.py` (mock) | `research_questions/sources/claims/conflicts` + `research_*_candidates` | `RESEARCH_*` actions + `project_versions` (unlocked bump, PERF-06) | `tests/api/test_historical_research_api.py` | FD-V1 | MOCKED | V1-07, G-02/WF-02 |

### CHR — Characters

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-CHR-001** | Character Identity Profile (identity facet, §4.1) | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | WF-01 extraction | `entities` (category=character) | — | — | FD-V1 | PARTIAL (`entities`) | V1-10, FD-FR-025, G-05/WF-05 |
| **TFD-CHR-002** | Facial identity: front, side and ¾ references, features, expression references,… | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | — | — | — | — | FD-V1 | NOT_IMPL | V1-10, AC-008, G-05/WF-05 |
| **TFD-CHR-003** | Performance identity profile and reference videos | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | — | — | — | — | FD-V1 | NOT_IMPL | V1-10, G-05/WF-05 |
| **TFD-CHR-004** | Appearance and costume facet linking costumes, props/weapons, hair/makeup and… | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | — | — | — | — | FD-V1 | NOT_IMPL | V1-10, FD-FR-025, G-05/WF-05 |
| **TFD-CHR-005** | Characteristic-level provenance envelope `{source, status, confidence,… | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | — | — | — | — | FD-V1 | NOT_IMPL | V1-10, G-05/WF-05 |
| **TFD-CHR-006** | Character versions: approval creates an immutable version; edits create… | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | — | — | — | — | FD-V1 | NOT_IMPL | V1-10, FD-FR-044, G-05/WF-05 |
| **TFD-CHR-007** | Character states (scene- and timeline-specific: injury, fatigue, dirt, blood,… | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | — | — | — | — | FD-V1 | NOT_IMPL | V1-10, FD-FR-029, G-05/WF-05 |
| **TFD-CHR-008** | Character relationships graph | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | — | — | — | — | FD-V1 | NOT_IMPL | V1-10, G-05/WF-05 |
| **TFD-CHR-009** | Non-destructive link from `entities(category=character)` to `characters`.… | Director: define each character | §13-S5 | — | — | — | Character, CharacterVersion, CharacterState | — | — | — | — | FD-V1 | n/a (migration) | V1-10, G-05/WF-05 |

### PHY — Physical identity

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-PHY-001** | Physical Identity Profile per character (and per performer where consented)… | Costume/VFX lead: record body data with provenance | §13-S5 | — | — | — | PhysicalIdentityProfile, BodyMeasurement | — | — | — | — | FD-V1 | NOT_IMPL | V1-11 |
| **TFD-PHY-002** | `body_measurements` rows: value, unit, capture method, date, source asset,… | Costume/VFX lead: record body data with provenance | §13-S5 | — | — | — | PhysicalIdentityProfile, BodyMeasurement | — | — | — | — | FD-V1 | NOT_IMPL | V1-11 |
| **TFD-PHY-003** | Manual entry and manual correction (a correction creates a new version) | Costume/VFX lead: record body data with provenance | §13-S5 | — | — | — | PhysicalIdentityProfile, BodyMeasurement | — | — | — | — | FD-V1 | NOT_IMPL | V1-11 |
| **TFD-PHY-004** | Labelling rule: any AI- or tool-estimated value is `estimated`. `verified`… | Costume/VFX lead: record body data with provenance | §13-S5 | — | — | — | PhysicalIdentityProfile, BodyMeasurement | — | — | — | — | FD-V1 | NOT_IMPL | V1-11 |
| **TFD-PHY-005** | Import from body-scanning tools: manual file import first, connected only after… | Costume/VFX lead: record body data with provenance | §13-S5 | — | — | — | PhysicalIdentityProfile, BodyMeasurement | — | — | — | — | FD-V2 | NOT_IMPL | V2-11 |
| **TFD-PHY-006** | Performer measurements need an active `reference_storage` consent before they… | Costume/VFX lead: record body data with provenance | §13-S5 | — | — | — | PhysicalIdentityProfile, BodyMeasurement | — | — | — | — | FD-V1 | NOT_IMPL | V1-11 |
| **TFD-PHY-007** | AI-assisted estimation from permitted images or video with stated capture… | Costume/VFX lead: record body data with provenance | §13-S5 | — | — | — | PhysicalIdentityProfile, BodyMeasurement | — | — | — | — | FD-V2 | NOT_IMPL | V2-11 |

### CNS — Consent

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-CNS-001** | Performer registry (`performers`), separate from characters, linked to… | Producer/Legal: authorise use of a real person | §13-S5 | — | — | — | Performer, PerformerConsent | — | — | — | — | FD-V1 | NOT_IMPL | — |
| **TFD-CNS-002** | Consent records: explicit, purpose-specific (§4.4 purposes), versioned,… | Producer/Legal: authorise use of a real person | §13-S5 | — | — | — | Performer, PerformerConsent | — | — | — | — | FD-V1 | NOT_IMPL — **gate DEC-012, DEC-007** | — |
| **TFD-CNS-003** | Server-side consent gate before every gated purpose (reference storage,… | Producer/Legal: authorise use of a real person | §13-S5 | — | — | — | Performer, PerformerConsent | — | — | — | — | FD-V1/V2 | NOT_IMPL | FD-FR-059 |
| **TFD-CNS-004** | Revocation: blocks new uses immediately; flags dependent assets, packages, jobs… | Producer/Legal: authorise use of a real person | §13-S5 | — | — | — | Performer, PerformerConsent | — | — | — | — | FD-V1 | NOT_IMPL | — |
| **TFD-CNS-005** | Voice consent is separate. Permission for recorded audio never implies… | Producer/Legal: authorise use of a real person | §13-S5 | — | — | — | Performer, PerformerConsent | — | — | — | — | FD-V1 | NOT_IMPL | — |
| **TFD-CNS-006** | Expiry handling and advance notice | Producer/Legal: authorise use of a real person | §13-S5 | — | — | — | Performer, PerformerConsent | — | — | — | — | FD-V2 | NOT_IMPL | — |
| **TFD-CNS-007** | Consent enforced at connected submission, re-checked at submit time (not only… | Producer/Legal: authorise use of a real person | §13-S5 | — | — | — | Performer, PerformerConsent | — | — | — | — | FD-V2 | NOT_IMPL | — |
| **TFD-CNS-008** | Provider data disclosure: before performer material is sent to a provider, show… | Producer/Legal: authorise use of a real person | §13-S5 | — | — | — | Performer, PerformerConsent | — | — | — | — | FD-V2 | NOT_IMPL | FD-FR-059 |

### DH — Digital humans

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-DH-001** | Digital double creation workflow (identity-preserving): select performer and… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-08, Master example |
| **TFD-DH-002** | Fictional avatar from a performer: the director selects which characteristics… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-08 |
| **TFD-DH-003** | Both avatar modes coexist in one project, chosen per performer↔character link | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-08 |
| **TFD-DH-004** | Performance-preserving transformation: source footage → external tool → output… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-07 |
| **TFD-DH-005** | Reusable digital human record (model asset, facial identity, body,… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-08 |
| **TFD-DH-006** | Workflow selection (transformation / digital human / both), with a Tattva… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-08 |
| **TFD-DH-007** | AI anchor workflow: real anchor → AI anchor (HeyGen candidate, UNVERIFIED),… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-09 |
| **TFD-DH-008** | Motion capture handoff and import (Rokoko, Move AI candidates, UNVERIFIED) as… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-10 |
| **TFD-DH-009** | Reusing a digital human in another project needs `future_project_reuse` consent… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V2 | NOT_IMPL | V2-08 |
| **TFD-DH-010** | Avatar *specification* (method intent, preserved characteristics, reference… | Director: create and reuse digital humans | §13-S5, S9 | — | — | — | DigitalHuman, AvatarVersion | — | — | — | — | FD-V1 | NOT_IMPL | — |

### CST — Costume

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-CST-001** | Costume Bible: garments, armour, accessories, footwear, jewellery, hair and… | Costume designer: define costumes and states | §13-S6 | — | — | — | Costume, CostumeState | — | — | — | — | FD-V1 | NOT_IMPL | V1-12, FD-FR-025 |
| **TFD-CST-002** | Costume states (condition, damage, scene variants) | Costume designer: define costumes and states | §13-S6 | — | — | — | Costume, CostumeState | — | — | — | — | FD-V1 | NOT_IMPL | V1-12, FD-FR-029 |
| **TFD-CST-003** | Costume assignment per character, scene and state | Costume designer: define costumes and states | §13-S6 | — | — | — | Costume, CostumeState | — | — | — | — | FD-V1 | NOT_IMPL | V1-12 |

### PRP — Props & weapons

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-PRP-001** | Props and weapons register (`kind` = `prop` or `weapon`; type, design,… | Props master: register props and weapons | §13-S6 | — | — | — | Prop, PropState | — | — | — | — | FD-V1 | NOT_IMPL | V1-13, FD-FR-025 |
| **TFD-PRP-002** | Prop states per scene (position, condition, state, holder) | Props master: register props and weapons | §13-S6 | — | — | — | Prop, PropState | — | — | — | — | FD-V1 | NOT_IMPL | V1-13, FD-FR-029 |
| **TFD-PRP-003** | Evidence links for historical props and weapons | Props master: register props and weapons | §13-S6 | — | — | — | Prop, PropState | — | — | — | — | FD-V1 | NOT_IMPL | V1-13 |

### ENV — Environment & location

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-ENV-001** | Location and environment profiles (geography, architecture, layout, terrain,… | Production designer: define locations | §13-S6 | — | — | — | Location, EnvironmentProfile, EnvironmentState | — | `scenes.location_name`, `entities` (category=location) | — | — | FD-V1 | PARTIAL (`scenes.location_name`, `entities`) | V1-14, FD-FR-025 |
| **TFD-ENV-002** | Environment states (weather, time of day, environmental change, damage) | Production designer: define locations | §13-S6 | — | — | — | Location, EnvironmentProfile, EnvironmentState | — | — | — | — | FD-V1 | NOT_IMPL | V1-14, FD-FR-029 |
| **TFD-ENV-003** | Background/reference library per location | Production designer: define locations | §13-S6 | — | — | — | Location, EnvironmentProfile, EnvironmentState | — | — | — | — | FD-V1 | NOT_IMPL | V1-14 |
| **TFD-ENV-004** | Non-destructive link from `scenes.location_name` and… | Production designer: define locations | §13-S6 | — | — | — | Location, EnvironmentProfile, EnvironmentState | — | — | — | — | FD-V1 | n/a | V1-14 |

### SB — Storyboard

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-SB-001** | Storyboard ingestion from images or PDF into ordered panels (page/panel crop… | Director: map storyboard to scenes and shots | §13-S7 | — | — | — | StoryboardPanel | — | — | — | — | FD-V1 | NOT_IMPL (CODE-05) | V1-15, FD-FR-021, G-03/WF-03 |
| **TFD-SB-002** | Text-brief panel generation (current WF-03) retained and labelled… | Director: map storyboard to scenes and shots | §13-S7 | `apps/ui/views/storyboard.py`, `views/review.py` | `apps/api/routers/storyboard.py` GET `/storyboard/panels`; `apps/api/routers/workflows.py` storyboard-intelligence | `packages/services/storyboard.py`, `packages/services/storyboard_review.py` | StoryboardPanel | WF-03 `packages/workflows/storyboard_intelligence/graph.py`, `aligner.py` | `storyboard_panels`, `storyboard_panel_candidates` | `STORYBOARD_COMMITTED/REJECTED` + `project_versions` | `tests/api/test_storyboard_api.py` | FD-V1 | VERIFIED (deterministic; `StoryboardAligner`) | V1-15, G-03/WF-03 |
| **TFD-SB-003** | Many-to-many panel ↔ scene ↔ shot mapping with human correction | Director: map storyboard to scenes and shots | §13-S7 | `apps/ui/views/storyboard.py`, `views/review.py` | `apps/api/routers/storyboard.py` GET `/storyboard/panels`; `apps/api/routers/workflows.py` storyboard-intelligence | `packages/services/storyboard.py`, `packages/services/storyboard_review.py` | StoryboardPanel | WF-03 `packages/workflows/storyboard_intelligence/graph.py`, `aligner.py` | `storyboard_panels`, `storyboard_panel_candidates` | `STORYBOARD_COMMITTED/REJECTED` + `project_versions` | `tests/api/test_storyboard_api.py` | FD-V1 | PARTIAL (`storyboard_panels.scene_id` single FK) | V1-15, FD-FR-022, G-03/WF-03 |
| **TFD-SB-004** | Panel approval, ordering and notes through candidates (existing pattern) | Director: map storyboard to scenes and shots | §13-S7 | `apps/ui/views/storyboard.py`, `views/review.py` | `apps/api/routers/storyboard.py` GET `/storyboard/panels`; `apps/api/routers/workflows.py` storyboard-intelligence | `packages/services/storyboard.py`, `packages/services/storyboard_review.py` | StoryboardPanel | WF-03 `packages/workflows/storyboard_intelligence/graph.py`, `aligner.py` | `storyboard_panels`, `storyboard_panel_candidates` | `STORYBOARD_COMMITTED/REJECTED` + `project_versions` | `tests/api/test_storyboard_api.py` | FD-V1 | VERIFIED | V1-15, G-03/WF-03 |

### CIN — Cinematography & Film Bible

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-CIN-001** | Camera/lens specification on a shot: extensible `camera_spec` JSONB covering… | DoP: define camera language and visual rules | §13-S7 | — | — | — | CameraSpec, CinematographyProfile, VisualRule | — | — | — | — | FD-V1 | NOT_IMPL | V1-17, Master example, G-06/WF-06 |
| **TFD-CIN-002** | Virtual cinematography fields (§7.2), `spec_kind=virtual` | DoP: define camera language and visual rules | §13-S7 | — | — | — | CameraSpec, CinematographyProfile, VisualRule | — | — | — | — | FD-V1 | NOT_IMPL | V1-17, G-06/WF-06 |
| **TFD-CIN-003** | `metadata_origin ∈ {actual, creative_target, recommended}` on every camera… | DoP: define camera language and visual rules | §13-S7 | — | — | — | CameraSpec, CinematographyProfile, VisualRule | — | — | — | — | FD-V1 | NOT_IMPL | V1-17, G-06/WF-06 |
| **TFD-CIN-004** | Recommendations from a described intent (shot type, position, lens, movement,… | DoP: define camera language and visual rules | §13-S7 | — | — | — | CameraSpec, CinematographyProfile, VisualRule | — | — | — | — | FD-V1 | NOT_IMPL | V1-17, G-06/WF-06 |
| **TFD-CIN-005** | Cinematography Bible: camera package, lens library, lighting library,… | DoP: define camera language and visual rules | §13-S7 | — | — | — | CameraSpec, CinematographyProfile, VisualRule | — | — | — | — | FD-V1 | NOT_IMPL | V1-16, G-06/WF-06 |
| **TFD-CIN-006** | Cinematography continuity across shots unless the director approves a change… | DoP: define camera language and visual rules | §13-S7 | — | — | — | CameraSpec, CinematographyProfile, VisualRule | — | — | — | — | FD-V1 | NOT_IMPL | V1-16, G-06/WF-06 |
| **TFD-CIN-010** | Film Bible visual rules (category, strictness) via synthesis → candidates →… | DoP: define camera language and visual rules | §13-S7 | `apps/ui/views/film_bible.py` (WIP) | `apps/api/routers/film_bible.py` GET/POST `/film-bible/rules` (WIP); `apps/api/routers/workflows.py` film-bible-synthesis | `packages/services/film_bible.py`, `packages/services/film_bible_review.py` (WIP) | CameraSpec, CinematographyProfile, VisualRule | WF-04 `packages/workflows/film_bible_synthesis/` (WIP, G04-A..G) | `film_bible_rules`, `film_bible_rule_candidates` (migration `00b7cd57e036`, uncommitted) | `VISUAL_RULE_CREATED`, `FILM_BIBLE_COMMITTED/REJECTED` | `tests/api/test_film_bible_api.py` (4 fail, 1 error); `tests/workflows/test_worker.py` (1 fail) | FD-V1 | BROKEN (G04-A/B) — **gate DEC-010** | V1-09, G-04/WF-04 |
| **TFD-CIN-011** | Film Bible rules link to research claims by ID and are tenant-checked | DoP: define camera language and visual rules | §13-S7 | `apps/ui/views/film_bible.py` (WIP) | `apps/api/routers/film_bible.py` GET/POST `/film-bible/rules` (WIP); `apps/api/routers/workflows.py` film-bible-synthesis | `packages/services/film_bible.py`, `packages/services/film_bible_review.py` (WIP) | CameraSpec, CinematographyProfile, VisualRule | WF-04 `packages/workflows/film_bible_synthesis/` (WIP, G04-A..G) | `film_bible_rules`, `film_bible_rule_candidates` (migration `00b7cd57e036`, uncommitted) | `VISUAL_RULE_CREATED`, `FILM_BIBLE_COMMITTED/REJECTED` | `tests/api/test_film_bible_api.py` (4 fail, 1 error); `tests/workflows/test_worker.py` (1 fail) | FD-V1 | BROKEN (G04-E, `create_rule(historical_claim_id)`) | V1-09, G-04/WF-04 |
| **TFD-CIN-012** | Manual rule creation goes through approval or a role-gated audited path.… | DoP: define camera language and visual rules | §13-S7 | `apps/ui/views/film_bible.py` (WIP) | `apps/api/routers/film_bible.py` GET/POST `/film-bible/rules` (WIP); `apps/api/routers/workflows.py` film-bible-synthesis | `packages/services/film_bible.py`, `packages/services/film_bible_review.py` (WIP) | CameraSpec, CinematographyProfile, VisualRule | WF-04 `packages/workflows/film_bible_synthesis/` (WIP, G04-A..G) | `film_bible_rules`, `film_bible_rule_candidates` (migration `00b7cd57e036`, uncommitted) | `VISUAL_RULE_CREATED`, `FILM_BIBLE_COMMITTED/REJECTED` | `tests/api/test_film_bible_api.py` (4 fail, 1 error); `tests/workflows/test_worker.py` (1 fail) | FD-V1 | BROKEN (G04-D/F) | V1-09, G-04/WF-04 |
| **TFD-CIN-013** | Visual Language Profile (palette, texture, lighting style, realism level, film… | DoP: define camera language and visual rules | §13-S7 | — | — | — | CameraSpec, CinematographyProfile, VisualRule | — | — | — | — | FD-V1 | NOT_IMPL | V1-09, G-04/WF-04 |

### SEQ — Sequences

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-SEQ-001** | Sequences: ordered scene groups with dramatic goal, emotion, mode override and… | Director: plan sequences | §13-S8 | — | — | — | Sequence | — | — | — | — | FD-V1 | NOT_IMPL | V1-18, FD-FR-028, G-06/WF-06 |
| **TFD-SEQ-002** | Scene planning: creative intention, entering and exiting character and… | Director: plan sequences | §13-S8 | — | — | — | Sequence | — | — | — | — | FD-V1 | NOT_IMPL | V1-18, FD-FR-029, G-06/WF-06 |

### SHT — Shots

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-SHT-001** | Shots: per-scene ordered shot list with type, composition, duration, action,… | Director: plan and specify shots | §13-S8, S9 | — | — | — | Shot, ShotSpec | — | `storyboard_panels.shot_type` (`ShotType` enum) | — | — | FD-V1 | PARTIAL (`storyboard_panels.shot_type`) | V1-19, FD-FR-028, G-06/WF-06 |
| **TFD-SHT-002** | `production_method ∈ {fully_ai_generated, live_action_chroma,… | Director: plan and specify shots | §13-S8, S9 | — | — | — | Shot, ShotSpec | — | — | — | — | FD-V1 | NOT_IMPL | V1-19, G-06/WF-06 |
| **TFD-SHT-003** | Provider-neutral Shot Specification: a versioned schema… | Director: plan and specify shots | §13-S8, S9 | — | — | — | Shot, ShotSpec | — | — | — | — | FD-V1 | NOT_IMPL | V1-23, FD-FR-028/032, G-06/WF-06 |
| **TFD-SHT-004** | Incoming and outgoing state per shot (character, costume, prop, geography,… | Director: plan and specify shots | §13-S8, S9 | — | — | — | Shot, ShotSpec | — | — | — | — | FD-V1 | NOT_IMPL | V1-19, FD-FR-029, G-06/WF-06 |
| **TFD-SHT-005** | Shot approval and versioning; an approved shot spec is immutable | Director: plan and specify shots | §13-S8, S9 | — | — | — | Shot, ShotSpec | — | — | — | — | FD-V1 | NOT_IMPL | V1-19, FD-FR-044, G-06/WF-06 |
| **TFD-SHT-006** | Convert storyboard panels into shot candidates | Director: plan and specify shots | §13-S8, S9 | — | — | — | Shot, ShotSpec | — | — | — | — | FD-V1 | NOT_IMPL | V1-19, G-06/WF-06 |

### CON — Continuity

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-CON-001** | Continuity validation: run checks (deterministic rules first, AI-assisted where… | Script supervisor: keep continuity | §13-S14 | — | — | — | ContinuityRule, ContinuityFinding, ContinuityDecision | — | — | — | — | FD-V1 | NOT_IMPL | V1-20, FD-FR-031, Master example, G-07/WF-07 |
| **TFD-CON-002** | Director controls: lock characteristic, permit variation (with bounds), approve… | Script supervisor: keep continuity | §13-S14 | — | — | — | ContinuityRule, ContinuityFinding, ContinuityDecision | — | — | — | — | FD-V1 | NOT_IMPL | V1-20, G-07/WF-07 |
| **TFD-CON-003** | Status model with the nine states (§9) on rules, states and findings | Script supervisor: keep continuity | §13-S14 | — | — | — | ContinuityRule, ContinuityFinding, ContinuityDecision | — | — | — | — | FD-V1 | NOT_IMPL | V1-20, FD-FR-044, G-07/WF-07 |
| **TFD-CON-004** | All nine dimensions supported. Checks apply across mixed-mode boundaries (real… | Script supervisor: keep continuity | §13-S14 | — | — | — | ContinuityRule, ContinuityFinding, ContinuityDecision | — | — | — | — | FD-V1 | NOT_IMPL | V1-20, G-07/WF-07 |
| **TFD-CON-005** | Coverage transparency: "no issue detected" always states dimensions, scope and… | Script supervisor: keep continuity | §13-S14 | — | — | — | ContinuityRule, ContinuityFinding, ContinuityDecision | — | — | — | — | FD-V1 | NOT_IMPL | V1-20, AC-010, G-07/WF-07 |
| **TFD-CON-006** | `continuity_decisions` record the director's disposition and rationale. AI… | Script supervisor: keep continuity | §13-S14 | — | — | — | ContinuityRule, ContinuityFinding, ContinuityDecision | — | — | — | — | FD-V1 | NOT_IMPL | V1-20, G-07/WF-07 |
| **TFD-CON-007** | Output continuity comparison against approved references (identity, costume,… | Script supervisor: keep continuity | §13-S14 | — | — | — | ContinuityRule, ContinuityFinding, ContinuityDecision | — | — | — | — | FD-V2 | NOT_IMPL | V2-22, FD-FR-041, G-07/WF-07 |
| **TFD-CON-008** | Change impact analysis for any canonical change (character, date, environment,… | Script supervisor: keep continuity | §13-S14 | — | — | — | ContinuityRule, ContinuityFinding, ContinuityDecision | — | — | — | — | FD-V1 | NOT_IMPL | V1-20, FD-FR-030, G-07/WF-07 |

### CTX — Context Resolver

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-CTX-001** | Context Resolver: a deterministic service producing versioned, hashed… | System: give AI the right, versioned context | §13-S11 | — | — | — | ContextPackage | — | — | — | — | FD-V1 | NOT_IMPL | V1-21, FD-FR-034 |
| **TFD-CTX-002** | AI nodes consume context packages only. They never query the DB freely or read… | System: give AI the right, versioned context | §13-S11 | — | — | — | ContextPackage | — | — | — | — | FD-V1 | NOT_IMPL (G-04 reads claims by text) | V1-21 |
| **TFD-CTX-003** | Staleness: a context package or any artifact compiled from it becomes `stale`… | System: give AI the right, versioned context | §13-S11 | — | — | — | ContextPackage | — | — | — | — | FD-V1 | NOT_IMPL | V1-21, FD-FR-044 |
| **TFD-CTX-004** | "Context used / excluded" is inspectable from any AI output | System: give AI the right, versioned context | §13-S11 | — | — | — | ContextPackage | — | — | — | — | FD-V1 | NOT_IMPL | V1-21 |

### AID — AI Director & AI platform

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-AID-001** | AI Director review: prioritised findings (severity, confidence, evidence,… | Director: get reviewable AI findings | §13-S14 | — | — | — | AIRun, Finding | — | — | — | — | FD-V1 | NOT_IMPL | V1-22, FD-FR-031, G-08/WF-08 |
| **TFD-AID-002** | `ModelGateway` port with a deterministic mock adapter. All generators… | Director: get reviewable AI findings | §13-S14 | — | — | — | AIRun, Finding | — | — | — | — | FD-V1 | NOT_IMPL — provider choice **gate DEC-004** | V1-22, CODE-03, G-08/WF-08 |
| **TFD-AID-003** | Structured output validated against schemas. Invalid model output is rejected,… | Director: get reviewable AI findings | §13-S14 | — | — | — | AIRun, Finding | — | — | — | — | FD-V1 | NOT_IMPL | V1-22, G-08/WF-08 |
| **TFD-AID-004** | Untrusted-input isolation (prompt-injection controls, tool allowlists) before… | Director: get reviewable AI findings | §13-S14 | — | — | — | AIRun, Finding | — | — | — | — | FD-V1 | NOT_IMPL (SEC-11) | V1-22, G-08/WF-08 |
| **TFD-AID-005** | Capability golden sets and rubrics (story, research, character, cinematography,… | Director: get reviewable AI findings | §13-S14 | — | — | — | AIRun, Finding | — | — | — | — | FD-V1 | NOT_IMPL | V1-22, FD-FR-049, G-08/WF-08 |
| **TFD-AID-006** | Generator-mode label (`deterministic`, `mock`, `live:<model>`) on every run,… | Director: get reviewable AI findings | §13-S14 | — | — | — | AIRun, Finding | — | — | — | — | FD-V1 | NOT_IMPL (audit 04 §4.5) | V1-22, G-08/WF-08 |
| **TFD-AID-007** | Per-run AI cost and token budget with an observability record | Director: get reviewable AI findings | §13-S14 | — | — | — | AIRun, Finding | — | — | — | — | FD-V1 | NOT_IMPL | V1-22, G-08/WF-08 |

### PKG — Packages & prompt compiler

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-PKG-001** | Prompt compiler: Shot Spec + context package + target (a capability snapshot,… | Director: compile a provider-neutral package | §13-S11 | — | — | — | ProductionPackage, PromptVersion | — | — | — | — | FD-V1 | NOT_IMPL | V1-24, FD-FR-032, G-09/WF-09 |
| **TFD-PKG-002** | Immutable production package: manifest per Gap §7.5 (IDs, versions, screenplay… | Director: compile a provider-neutral package | §13-S11 | — | — | — | ProductionPackage, PromptVersion | — | — | — | — | FD-V1 | NOT_IMPL | V1-25, FD-FR-037/052, G-09/WF-09 |
| **TFD-PKG-003** | Validation against the target's capability snapshot or manual target notes.… | Director: compile a provider-neutral package | §13-S11 | — | — | — | ProductionPackage, PromptVersion | — | — | — | — | FD-V1 | NOT_IMPL | V1-24, FD-FR-033, G-09/WF-09 |
| **TFD-PKG-004** | A package goes `stale` when any source version changes. Recompiling creates a… | Director: compile a provider-neutral package | §13-S11 | — | — | — | ProductionPackage, PromptVersion | — | — | — | — | FD-V1 | NOT_IMPL | V1-25, FD-FR-034, G-09/WF-09 |
| **TFD-PKG-005** | Project Master Direction as a compiler input | Director: compile a provider-neutral package | §13-S11 | — | — | — | ProductionPackage, PromptVersion | — | — | — | — | FD-V1 | NOT_IMPL | V1-24, FD-FR-028, G-09/WF-09 |
| **TFD-PKG-006** | Tool recommendation per task or shot over the §12.4 criteria with explained… | Director: compile a provider-neutral package | §13-S11 | — | — | — | ProductionPackage, PromptVersion | — | — | — | — | FD-V1/V2 | NOT_IMPL | V1-24, G-09/WF-09 |
| **TFD-PKG-007** | Packages embed consent and rights status. A package that references performer… | Director: compile a provider-neutral package | §13-S11 | — | — | — | ProductionPackage, PromptVersion | — | — | — | — | FD-V1 | NOT_IMPL | V1-25, FD-FR-059, G-09/WF-09 |

### INT — Integrations & registry

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-INT-001** | Manual provider handoff: copy prompt and settings; download JSON + Markdown… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V1 | NOT_IMPL | V1-26, FD-FR-039/053, Master example, G-10/WF-10 |
| **TFD-INT-002** | Connected provider execution via a provider adapter (API and MCP are separate):… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V2 | NOT_IMPL — **gate DEC-013, DEC-006** | V2-01, V2-13, FD-FR-035/036, Master example, G-10/WF-10 |
| **TFD-INT-003** | Production Tool Registry with versioned capability snapshots (Master §12.3… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V1/V2 | NOT_IMPL | V1-26, V2-19, FD-FR-033, G-10/WF-10 |
| **TFD-INT-004** | Every task has an explicit execution mode (`CONNECTED_API`, `CONNECTED_MCP`,… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V1 | NOT_IMPL | V1-26, FD-FR-051, G-10/WF-10 |
| **TFD-INT-005** | Provider onboarding gate (terms/rights, auth, capability contract, lifecycle,… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V2 | NOT_IMPL | V2-19, Gap §7.4, G-10/WF-10 |
| **TFD-INT-006** | Terms compliance: no automation that a provider's terms prohibit (Midjourney is… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V1 | n/a | V1-26, Gap §7.2, G-10/WF-10 |
| **TFD-INT-007** | Provider credentials live server-side in a secret store, are never in DB… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V2 | NOT_IMPL (keys in `config.py` unused) | V2-19, G-10/WF-10 |
| **TFD-INT-008** | When a provider is disconnected, disallowed or down, the same package version… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V2 | NOT_IMPL | V2-19, Gap §8.2, G-10/WF-10 |
| **TFD-INT-009** | Webhook signature verification and replay protection | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V2 | NOT_IMPL | V2-19, G-10/WF-10 |
| **TFD-INT-010** | Live MCP tool and schema discovery at connect time. A snapshot diff blocks… | Producer: run tools manually or connected | §13-S12 | — | — | — | Provider, CapabilitySnapshot, ProviderConnection | — | — | — | — | FD-V2 | NOT_IMPL | V2-19, FD-FR-036, G-10/WF-10 |

### GEN — Generation jobs

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-GEN-001** | `generation_jobs` per package execution with states (`draft, awaiting_approval,… | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | `workflow_runs` + `outbox_tasks` (internal graphs only) | — | — | FD-V2 | SCAFFOLD (`workflow_runs` internal only) | V2-17, FD-FR-040 |
| **TFD-GEN-002** | `generation_attempts` with idempotency key, provider request ID, timestamps and… | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-18, FD-FR-056 |
| **TFD-GEN-003** | Unknown-outcome reconciliation before any retry. Tattva never auto-resubmits a… | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-18, FD-FR-056 |
| **TFD-GEN-004** | Cost estimate (where the provider exposes it, otherwise "unknown" is shown) and… | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-20, FD-FR-038/055 |
| **TFD-GEN-005** | Character reference generation (identity sheets, turnarounds) as candidate… | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-01, V2-03 |
| **TFD-GEN-006** | Keyframe workflows (approved keyframe → video package reference) | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-06 |
| **TFD-GEN-007** | Video generation through verified adapters with duration, aspect, seed and… | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-13, FD-FR-035 |
| **TFD-GEN-008** | Manual and connected parity: a manual run produces the same job, attempt, asset… | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-02, FD-FR-051/053 |
| **TFD-GEN-009** | Cancel where the provider supports it; otherwise record "cancellation… | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-17, FD-FR-048 |
| **TFD-GEN-010** | Environment reference production linked to location and environment state | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-04 |
| **TFD-GEN-011** | Costume and prop reference production linked to costume, prop and state | Producer: track every generation and its cost | §13-S12 | — | — | — | GenerationJob, GenerationAttempt | — | — | — | — | FD-V2 | NOT_IMPL | V2-05 |

### HYB — Hybrid / on-set

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-HYB-001** | Chroma capture plan per scene or shot, generated from method, environment,… | 1st AD/VFX sup: plan and ingest live-action capture | §13-S10 | — | — | — | CapturePlan, CaptureManifest, ProductionFootage | — | — | — | — | FD-V2 | NOT_IMPL | V2-12, Master example |
| **TFD-HYB-002** | Capture manifest per planned shoot with the §8.3 fields and an approval status | 1st AD/VFX sup: plan and ingest live-action capture | §13-S10 | — | — | — | CapturePlan, CaptureManifest, ProductionFootage | — | — | — | — | FD-V2 | NOT_IMPL | V2-12 |
| **TFD-HYB-003** | Independent shoot ingestion and analysis (the §8.2 issue list) producing… | 1st AD/VFX sup: plan and ingest live-action capture | §13-S10 | — | — | — | CapturePlan, CaptureManifest, ProductionFootage | — | — | — | — | FD-V2 | NOT_IMPL | V2-12 |
| **TFD-HYB-004** | Captured footage linked to manifest items; missing-requirement validation | 1st AD/VFX sup: plan and ingest live-action capture | §13-S10 | — | — | — | CapturePlan, CaptureManifest, ProductionFootage | — | — | — | — | FD-V2 | NOT_IMPL | V2-12 |
| **TFD-HYB-005** | Actual camera metadata extracted from footage, stored as… | 1st AD/VFX sup: plan and ingest live-action capture | §13-S10 | — | — | — | CapturePlan, CaptureManifest, ProductionFootage | — | — | — | — | FD-V2 | NOT_IMPL | V2-12 |

### OUT — Output import & inspection

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-OUT-001** | Manual output import: upload → validate → immutable asset → map to package,… | Director: import, inspect and decide on outputs | §13-S13, S14 | — | — | — | ImportJob, OutputReview, RevisionRequest | — | — | — | — | FD-V1 | NOT_IMPL | V1-27, FD-FR-053/057, G-11/WF-11 |
| **TFD-OUT-002** | Output inspection against the Shot Spec and approved references over the Stage… | Director: import, inspect and decide on outputs | §13-S13, S14 | — | — | — | ImportJob, OutputReview, RevisionRequest | — | — | — | — | FD-V1/V2 | NOT_IMPL | V1-27, V2-21, FD-FR-041, G-11/WF-11 |
| **TFD-OUT-003** | For transformation outputs, inspection against the original performance… | Director: import, inspect and decide on outputs | §13-S13, S14 | — | — | — | ImportJob, OutputReview, RevisionRequest | — | — | — | — | FD-V2 | NOT_IMPL | V2-21, G-11/WF-11 |
| **TFD-OUT-004** | Human disposition (approve, reject, request revision) with reason. Approval… | Director: import, inspect and decide on outputs | §13-S13, S14 | — | — | — | ImportJob, OutputReview, RevisionRequest | — | — | — | — | FD-V1 | NOT_IMPL | V1-27, FD-FR-058, G-11/WF-11 |
| **TFD-OUT-005** | Revision request creates a new package version and job; the original output and… | Director: import, inspect and decide on outputs | §13-S13, S14 | — | — | — | ImportJob, OutputReview, RevisionRequest | — | — | — | — | FD-V1/V2 | NOT_IMPL | V1-27, V2-23, FD-FR-042/058, G-11/WF-11 |
| **TFD-OUT-006** | Missing metadata on imports is entered by the user and labelled… | Director: import, inspect and decide on outputs | §13-S13, S14 | — | — | — | ImportJob, OutputReview, RevisionRequest | — | — | — | — | FD-V1 | NOT_IMPL | V1-27, G-11/WF-11 |

### LIB — Production library

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-LIB-001** | Production asset library of approved images, keyframes, videos, audio, digital… | Editor: find approved production assets | §13-S15 | — | — | — | Asset (approved), Lineage | — | — | — | — | FD-V2 | NOT_IMPL | V2-24 |
| **TFD-LIB-002** | Lineage view: asset → package → job/attempt → provider/model/params → review →… | Editor: find approved production assets | §13-S15 | — | — | — | Asset (approved), Lineage | — | — | — | — | FD-V2 | NOT_IMPL | V2-24, FD-FR-057 |
| **TFD-LIB-003** | Org-level shared library for reusable assets and digital humans, honouring… | Editor: find approved production assets | §13-S15 | — | — | — | Asset (approved), Lineage | — | — | — | — | FD-V2 | NOT_IMPL | V2-24 |

### VOC — Voice & dialogue

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-VOC-001** | Voice source per character or scene (`original_recorded` or `ai_authorised`);… | Sound lead: manage dialogue and voices | §13-S12 | — | — | — | VoiceProfile, DialogueSegment | — | — | — | — | FD-V1/V2 | NOT_IMPL | V2-14 |
| **TFD-VOC-002** | Original audio linked to scene, character and dialogue segment; takes and… | Sound lead: manage dialogue and voices | §13-S12 | — | — | — | VoiceProfile, DialogueSegment | — | — | — | — | FD-V2 | NOT_IMPL | V2-14 |
| **TFD-VOC-003** | Voice profiles (consented clone or fictional voice), emotion/delivery, language… | Sound lead: manage dialogue and voices | §13-S12 | — | — | — | VoiceProfile, DialogueSegment | — | — | — | — | FD-V2 | NOT_IMPL | V2-14 |
| **TFD-VOC-004** | Voice clone and generated speech blocked without the corresponding consent… | Sound lead: manage dialogue and voices | §13-S12 | — | — | — | VoiceProfile, DialogueSegment | — | — | — | — | FD-V2 | NOT_IMPL | V2-14 |
| **TFD-VOC-005** | Localised scripts are separate approved assets linked to screenplay version and… | Sound lead: manage dialogue and voices | §13-S12 | — | — | — | VoiceProfile, DialogueSegment | — | — | — | — | FD-V2 | NOT_IMPL | V2-15 |
| **TFD-VOC-006** | Dubbing and lip-sync via external tools (manual first; Sync Labs is a… | Sound lead: manage dialogue and voices | §13-S12 | — | — | — | VoiceProfile, DialogueSegment | — | — | — | — | FD-V2 | NOT_IMPL | V2-16 |
| **TFD-VOC-007** | Dialogue comparison (original vs translation vs generated) | Sound lead: manage dialogue and voices | §13-S12 | — | — | — | VoiceProfile, DialogueSegment | — | — | — | — | FD-V2 | NOT_IMPL | V2-15 |

### POST — Post handoff & export

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-POST-001** | Post handoff package containing every §11 item (approved footage, IDs,… | Editor: receive an organised handoff | §13-S16 | — | — | — | HandoffManifest, Export | — | — | — | — | FD-V2 | NOT_IMPL | V2-25 |
| **TFD-POST-002** | Interchange formats: JSON and CSV manifests plus a media folder. Other formats… | Editor: receive an organised handoff | §13-S16 | — | — | — | HandoffManifest, Export | — | — | — | — | FD-V2 | NOT_IMPL | V2-25 |
| **TFD-POST-003** | Editorial notes per shot | Editor: receive an organised handoff | §13-S16 | — | — | — | HandoffManifest, Export | — | — | — | — | FD-V2 | NOT_IMPL | V2-25 |
| **TFD-POST-004** | Project archive export of approved artifacts, lineage, evidence, prompts,… | Editor: receive an organised handoff | §13-S16 | — | — | — | HandoffManifest, Export | — | — | — | — | FD-V1 | NOT_IMPL | FD-FR-050/060 |

### APR — Approvals

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-APR-001** | Generalised `approval_requests`: scope, `target_type`/`target_id`, target… | Approver: decide with authority | §13-S14 | `apps/ui/views/review.py` | `apps/api/routers/approvals.py` POST `/approvals/{id}/decide` (scope dispatch; `else` → script service) | per-service `decide()`; `ApprovalRepository.get_scoped(for_update=True)` | ApprovalRequest | — | `approval_requests` | `AuditAction.APPROVAL_DECIDED` | G-01..G-03 slice tests | FD-V1 | PARTIAL (single tier) | V1-28, FD-FR-044 |
| **TFD-APR-002** | Explicit scope dispatch. An unknown scope returns 422 and is never routed to… | Approver: decide with authority | §13-S14 | `apps/ui/views/review.py` | `apps/api/routers/approvals.py` POST `/approvals/{id}/decide` (scope dispatch; `else` → script service) | per-service `decide()`; `ApprovalRepository.get_scoped(for_update=True)` | ApprovalRequest | — | `approval_requests` | `AuditAction.APPROVAL_DECIDED` | G-01..G-03 slice tests | FD-V1 | DEFECT (SEC-08, `routers/approvals.py` else-branch) | V1-28 |
| **TFD-APR-003** | An approval binds to an exact target version. A mismatch returns 409 and forces… | Approver: decide with authority | §13-S14 | `apps/ui/views/review.py` | `apps/api/routers/approvals.py` POST `/approvals/{id}/decide` (scope dispatch; `else` → script service) | per-service `decide()`; `ApprovalRepository.get_scoped(for_update=True)` | ApprovalRequest | — | `approval_requests` | `AuditAction.APPROVAL_DECIDED` | G-01..G-03 slice tests | FD-V1 | PARTIAL (`assert_expected_version`) | V1-28, FD-FR-045 |
| **TFD-APR-004** | Partial approval (selected candidates) works in every workflow, including the… | Approver: decide with authority | §13-S14 | `apps/ui/views/review.py` | `apps/api/routers/approvals.py` POST `/approvals/{id}/decide` (scope dispatch; `else` → script service) | per-service `decide()`; `ApprovalRepository.get_scoped(for_update=True)` | ApprovalRequest | — | `approval_requests` | `AuditAction.APPROVAL_DECIDED` | G-01..G-03 slice tests | FD-V1 | VERIFIED WF-01..03; BROKEN WF-04 (G04-A) | V1-28 |
| **TFD-APR-005** | Decisions record the authenticated actor, capability, timestamp and notes. AI… | Approver: decide with authority | §13-S14 | `apps/ui/views/review.py` | `apps/api/routers/approvals.py` POST `/approvals/{id}/decide` (scope dispatch; `else` → script service) | per-service `decide()`; `ApprovalRepository.get_scoped(for_update=True)` | ApprovalRequest | — | `approval_requests` | `AuditAction.APPROVAL_DECIDED` | G-01..G-03 slice tests | FD-V1 | PARTIAL (unauthenticated actor) | V1-28, FD-FR-046 |
| **TFD-APR-006** | Cross-project approvals inbox filtered by the user's capabilities | Approver: decide with authority | §13-S14 | — | — | — | ApprovalRequest | — | — | — | — | FD-V1 | NOT_IMPL | V1-28 |
| **TFD-APR-007** | Multi-step approval chains (for example, creative sign-off then management… | Approver: decide with authority | §13-S14 | — | — | — | ApprovalRequest | — | — | — | — | FD-V1 | NOT_IMPL | V1-28 |

### VER — Versioning

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-VER-001** | Project version integrity: row lock on every bump and unique `(project_id,… | Anyone: trust versions | §13-S14 | — | — | `packages/domain/invariants.py::assert_expected_version`; lock only in `script_review.py:206` | ProjectVersion, *Version | — | `projects.current_version`, `project_versions` (no unique) | — | `tests/unit/test_invariants.py` | FD-V1 | DEFECT (PERF-06) | V1-29, FD-FR-045 |
| **TFD-VER-002** | Artifact versioning for screenplay, character, bible, shot spec, package,… | Anyone: trust versions | §13-S14 | — | — | `packages/domain/invariants.py::assert_expected_version`; lock only in `script_review.py:206` | ProjectVersion, *Version | — | `projects.current_version`, `project_versions` (no unique) | — | `tests/unit/test_invariants.py` | FD-V1 | PARTIAL | V1-29, FD-FR-044 |
| **TFD-VER-003** | Expected-version checks on all protected mutations | Anyone: trust versions | §13-S14 | — | — | `packages/domain/invariants.py::assert_expected_version`; lock only in `script_review.py:206` | ProjectVersion, *Version | — | `projects.current_version`, `project_versions` (no unique) | — | `tests/unit/test_invariants.py` | FD-V1 | PARTIAL | V1-29, FD-FR-045 |
| **TFD-VER-004** | Version relationship navigation (`derived_from`, `supersedes`) | Anyone: trust versions | §13-S14 | — | — | — | ProjectVersion, *Version | — | — | — | — | FD-V1 | NOT_IMPL | V1-29 |
| **TFD-VER-005** | Re-runs never duplicate canonical rows; they supersede them | Anyone: trust versions | §13-S14 | — | — | `packages/domain/invariants.py::assert_expected_version`; lock only in `script_review.py:206` | ProjectVersion, *Version | — | `projects.current_version`, `project_versions` (no unique) | — | `tests/unit/test_invariants.py` | FD-V1 | DEFECT (G04-F) | V1-29 |

### AUD — Audit

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-AUD-001** | Audit events for every material action (lock, revision, suggestion disposition,… | Auditor: reconstruct who did what | §13-S14 | `apps/ui/views/audit.py` | `apps/api/routers/projects.py` GET `/audit-log` | `AuditRepository.record` (17 `AuditAction`s) | AuditEvent | — | `audit_events` (mutable, SEC-07) | — | — | FD-V1 | PARTIAL (17 `AuditAction`s) | V1-29, FD-FR-046 |
| **TFD-AUD-002** | Audit is append-only at the DB level | Auditor: reconstruct who did what | §13-S14 | — | — | — | AuditEvent | — | — | — | — | FD-V1 | NOT_IMPL (SEC-07) | V1-29 |
| **TFD-AUD-003** | Audit view with filters and export | Auditor: reconstruct who did what | §13-S14 | `apps/ui/views/audit.py` | `apps/api/routers/projects.py` GET `/audit-log` | `AuditRepository.record` (17 `AuditAction`s) | AuditEvent | — | `audit_events` (mutable, SEC-07) | — | — | FD-V1 | PARTIAL (`apps/ui/views/audit.py` list) | V1-29 |
| **TFD-AUD-004** | Audit and analytics events never contain secrets, full script text or performer… | Auditor: reconstruct who did what | §13-S14 | — | — | — | AuditEvent | — | — | — | — | FD-V1 | n/a | V1-29 |

### OPS — Operations

| Req ID | Requirement | User story (role: goal) | Journey | Screen | API | Service | Domain model | Workflow | DB | Audit / version | Test | Release | Status (audit 02) | Aliases |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TFD-OPS-001** | Async-by-default workflows (202 + run ID + status endpoint); sync only in tests | Operator: run reliably and observably | cross-cutting | — | `apps/api/routers/workflows.py` GET `/workflow-runs/{run_id}`; `apps/api/schemas.py` `sync_execution=True` | — | OutboxTask, WorkflowRun | — | `workflow_runs` | — | — | FD-V1 | DEFECT (`sync_execution=True` default, PERF-01) | V1-30, FD-FR-047 |
| **TFD-OPS-002** | Worker lease and heartbeat, retry with exponential backoff and jitter, max… | Operator: run reliably and observably | cross-cutting | — | — | `apps/worker/worker.py::process_one_task`; `OutboxRepository.claim_next` (SKIP LOCKED) | OutboxTask, WorkflowRun | — | `outbox_tasks` | — | `tests/workflows/test_worker.py` | FD-V1 | NOT_IMPL (PERF-04) | V1-30, FD-FR-048 |
| **TFD-OPS-003** | Redelivery resumes from the checkpoint; candidate writes are idempotent | Operator: run reliably and observably | cross-cutting | — | — | `apps/worker/worker.py::process_one_task`; `OutboxRepository.claim_next` (SKIP LOCKED) | OutboxTask, WorkflowRun | — | `outbox_tasks` | — | `tests/workflows/test_worker.py` | FD-V1 | DEFECT (restart from START) | V1-30, FD-FR-048 |
| **TFD-OPS-004** | `Idempotency-Key` on resource-creating and cost-bearing POSTs | Operator: run reliably and observably | cross-cutting | — | — | — | OutboxTask, WorkflowRun | — | — | — | — | FD-V1 | NOT_IMPL | V1-30, FD-FR-048 |
| **TFD-OPS-005** | Task Centre with task states (queued, running, awaiting input, awaiting… | Operator: run reliably and observably | cross-cutting | — | — | — | OutboxTask, WorkflowRun | — | — | — | — | FD-V1 | NOT_IMPL | V1-30, FD-FR-047 |
| **TFD-OPS-006** | Observability: request/correlation IDs, structured logs, metrics, traces,… | Operator: run reliably and observably | cross-cutting | — | `apps/api/routers/health.py` `/health` | `packages/core/logging.py` | OutboxTask, WorkflowRun | — | — | — | — | FD-V1 | NOT_IMPL (PERF-07) | V1-30 |
| **TFD-OPS-007** | CI (lint, tests against Postgres, migration upgrade/downgrade round trip,… | Operator: run reliably and observably | cross-cutting | — | — | — | OutboxTask, WorkflowRun | — | — | — | — | FD-V1 | NOT_IMPL — DEC-015 | V1-30 |
| **TFD-OPS-008** | Backups and a tested restore before any pilot data | Operator: run reliably and observably | cross-cutting | — | — | — | OutboxTask, WorkflowRun | — | — | — | — | FD-V1 | NOT_IMPL | V1-30 |
| **TFD-OPS-009** | In-app notifications | Operator: run reliably and observably | cross-cutting | — | — | — | OutboxTask, WorkflowRun | — | — | — | — | FD-V1 | NOT_IMPL | V1-30, FD-DEC-019 |
| **TFD-OPS-010** | Cursor pagination on every list endpoint | Operator: run reliably and observably | cross-cutting | — | — | — | OutboxTask, WorkflowRun | — | — | — | — | FD-V1 | NOT_IMPL (PERF-05) | V1-30 |
## 5. Known traceability gaps and conflicts

| # | Issue | Effect | Action |
|---|---|---|---|
| 1 | Area code `AUD` is used for requirements (`TFD-AUD-001…004`), while the audit documents use the Doc IDs `TFD-AUD-001…010` | Ambiguous references | Recommend renaming the audit Doc IDs to `TFD-AUDIT-0nn` (docs only, no code impact). Raised for the decision register |
| 2 | Film Bible is filed under `CIN` (`TFD-CIN-010…013`) while WF-04 code lives in `film_bible_synthesis` | None, provided the alias column is kept | Keep the `G-04/WF-04` alias |
| 3 | 4 `BROKEN` and 5 `DEFECT` rows depend on Phase C defect fixes (G04-A..G, PERF-06, SEC-08, CODE-04) | They cannot move to VERIFIED until fixed | DEC-010 (gate #3) first |
| 4 | "Verified" rows are verified only with deterministic or mock generators and the unauthenticated header identity | They must be re-verified after ADR-003 (auth) and DEC-004 (real model) | The slice template re-runs them |
| 5 | Screens `S-*` are design IDs from the IA. The Streamlit views listed are the current partial realisations, not the target screens | — | ADR-002 governs the build |

## 6. Maintenance

- **Regeneration:** a script reads the PRD requirement table and this file's per-area targets and current-code overrides. Phase C adds it as `scripts/traceability.py`, and CI fails if a PRD ID is missing from the matrix or a `slice` pytest marker references an unknown ID.
- **When code lands:** update the current-code override for that ID in the same PR. The PR template asks "Which TFD IDs does this change? Is the matrix row updated?"
- **Status changes:** move to `VERIFIED` only with a CI run link (Master Prompt §29: "a requirement is not complete until the corresponding implementation and verification evidence exist").
