# API and Event Contracts — Tattva AI Film Director

**Doc ID:** TFD-ARC-005 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval

**Inputs:** `apps/api/main.py`, `apps/api/routers/*.py`, `apps/api/schemas.py`, `apps/api/errors.py`, `apps/api/dependencies.py`, `packages/domain/errors.py`; `docs/audit/03`; Master Prompt §5, §6.5, §7, §12, §14, §21; Gap Report §7.5; `LOW_LEVEL_DESIGN.md` §2, §5, §6; `DATABASE_DESIGN_AND_ERD.md` §3.

---

## 1. Conventions (target)

| Topic | Contract |
|---|---|
| Base path | `/api/v1` (exists; `settings.api_v1_str`). `/health/live` and `/health/ready` at root. The existing `/health` is kept as an alias of `live`. |
| Media types | Requests and responses: `application/json`. Errors: `application/problem+json` (§5). |
| Authentication | `Authorization: Bearer <JWT>` from the OIDC IdP (DEC-002). The API validates the signature (JWKS), `iss`, `aud`, `exp` and `nbf`. The `sub`/`iss` pair maps to `users.auth_subject`/`auth_issuer`. `X-Actor-ID` is accepted **only** when `AUTH_MODE=header_test` (test environment), and never by default. |
| Org context | Derived from the target resource (project → org) for project routes. Org-level routes (`GET /projects`, provider connections) use `X-Org-ID`, **validated against the caller's memberships**. It defaults to the only membership when there is exactly one. Client-supplied org IDs are never trusted on their own (this resolves CODE-02 in `docs/audit/10`). |
| Authorization | Each route declares one capability (§4). Denial returns `403 forbidden`. A resource in another tenant returns `404` (no oracle). |
| Idempotency | Header `Idempotency-Key: <uuid>` on mutating routes marked **IK** in §4. It is optional during migration and then required (missing returns `428`). Replays return the stored response plus `Idempotent-Replayed: true`. Reusing a key with a different body returns `422 idempotency-key-reuse` (LLD §5). |
| Async work | Routes marked **202** return `202 Accepted`, `Location: /api/v1/workflow-runs/{id}` (or `/generation-jobs/{id}`, `/imports/{id}`, `/exports/{id}`), and the resource body. Clients poll with `If-None-Match` (ETag = row `updated_at` hash) and get `304` when nothing changed. Server-Sent Events are a later option (SYSTEM_ARCHITECTURE §3.2). |
| Pagination | Cursor-based: `?limit=50&cursor=<opaque>`, max 200. The response is `{"items": [...], "next_cursor": "…" | null}`. The cursor encodes `(created_at, id)` (or the list's sort key) as base64 JSON, signed with an HMAC so it cannot be forged. |
| Concurrency | Mutations of versioned aggregates accept `If-Match: <etag>`. A mismatch returns `412`. Domain version conflicts return `409 version-conflict`. |
| Correlation | `X-Request-ID` is echoed or generated, appears in every problem body (`correlation_id`), and is logged and stored in `audit_events.request_id`. |
| Rate limits | `429` with `Retry-After`. Headers `RateLimit-Limit`/`RateLimit-Remaining`. AI-trigger and generation routes have tighter per-actor limits. |
| Time and IDs | RFC 3339 UTC timestamps; IDs are UUID strings (as today). |

---

## 2. Current route inventory (verified from `apps/api/routers/*`)

| # | Method + path | Router · service | Request | Response | Notes |
|---|---|---|---|---|---|
| 1 | `GET /health` | health · inline `SELECT 1` | — | `HealthResponse` | Root, not versioned |
| 2 | `POST /api/v1/projects` | projects · `ProjectService.create` | `ProjectCreateRequest{title, logline?, genre?}` | 201 `ProjectResponse` | |
| 3 | `GET /api/v1/projects` | `ProjectService.list` | — | `ProjectResponse[]` | Unpaginated |
| 4 | `GET /api/v1/projects/{project_id}` | `ProjectService.get` | — | `ProjectResponse` | Scoped |
| 5 | `GET /api/v1/projects/{project_id}/versions` | `ProjectService.versions` | — | `ProjectVersionResponse[]` | |
| 6 | `GET /api/v1/projects/{project_id}/audit-log` | `ProjectService.audit_log` | — | `AuditEventResponse[]` | |
| 7 | `GET /api/v1/projects/{project_id}/candidates` | `ProjectService.candidates` | — | `CandidatesResponse{scenes, entities, research_claims, research_questions, storyboard_panels, film_bible_rules, approvals}` | The router does not pass `film_bible_rules` (WIP) |
| 8 | `GET /api/v1/projects/{project_id}/scenes` | `ProjectService.canonical_scenes` | — | `SceneResponse[]` | Returns every generation (no supersede filter) |
| 9 | `GET /api/v1/projects/{project_id}/entities` | `ProjectService.canonical_entities` | — | `EntityResponse[]` | Same |
| 10 | `POST /api/v1/projects/{project_id}/assets/upload` | assets · `AssetService.upload` | multipart `file` | `AssetUploadResponse` (200) | Whole file in memory |
| 11 | `GET /api/v1/projects/{project_id}/assets` | `AssetService.list` | — | `AssetResponse[]` | |
| 12 | `POST /api/v1/projects/{project_id}/workflows/script-intelligence` | workflows · `ScriptIntelligenceService.start` | `{script_asset_id, sync_execution=true}` | `WorkflowTriggerResponse{workflow_run_id, status, approval_request_id?, candidate_summary}` | Sync by default |
| 13 | `POST …/workflows/historical-research` | `HistoricalResearchService.start` | `{topic, seed_text?, sync_execution=true}` | same | |
| 14 | `POST …/workflows/storyboard-intelligence` | `StoryboardIntelligenceService.start` | `{brief, sync_execution=true}` | same | |
| 15 | `POST …/workflows/film-bible-synthesis` (WIP) | `FilmBibleSynthesisService.start` | `{user_notes?, sync_execution=true}` | same | Broken (G04-B) |
| 16 | `GET /api/v1/workflow-runs/{run_id}` | `WorkflowRunRepository.get_scoped` | — | `WorkflowRunResponse` | |
| 17 | `POST /api/v1/approvals/{approval_id}/decide` | approvals · dispatch by `scope` | `ApprovalDecisionRequest{decision, notes?, approved_scene_ids?, approved_entity_ids?, approved_claim_ids?, approved_question_ids?, approved_panel_ids?, approved_rule_ids?}` | `ApprovalDecisionResponse{status, approval_id, decision, run_status, new_project_version}` | Unknown scope falls through to script (SEC-08) |
| 18 | `GET /api/v1/projects/{project_id}/research/questions?status=` | research · `ResearchService.list_questions` | — | `ResearchQuestionResponse[]` | |
| 19 | `POST …/research/questions` | `ResearchService.create_question` | `{text, category}` | `ResearchQuestionResponse` (200) | Direct canonical write (SEC-06) |
| 20 | `GET …/research/sources` | `ResearchService.list_sources` | — | `ResearchSourceResponse[]` | |
| 21 | `POST …/research/sources` | `ResearchService.create_source` | `{title, tier, author?, publication_year?, locator?, url?, asset_id?, reliability_notes?}` | `ResearchSourceResponse` | `asset_id` not tenant-validated (SEC-04) |
| 22 | `GET …/research/claims?claim_class=` | `ResearchService.list_claims` | — | `ResearchClaimResponse[]` | |
| 23 | `GET …/research/conflicts` | `ResearchService.list_conflicts` | — | `ResearchConflictResponse[]` | |
| 24 | `GET …/storyboard/panels` | storyboard · `StoryboardService.list_panels` | — | `StoryboardPanelResponse[]` | |
| 25 | `GET …/film-bible/rules?category=` (WIP) | film_bible · `FilmBibleService.list_rules` | — | `FilmBibleRuleResponse[]` | |
| 26 | `POST …/film-bible/rules` (WIP) | `FilmBibleService.create_rule` | `FilmBibleRuleCreateRequest` | `FilmBibleRuleResponse` | Bypasses approval (G04-D) |

There are no `PUT`, `PATCH` or `DELETE` routes. CORS allows `GET`/`POST` and the headers `Content-Type`, `X-Actor-ID` only (`main.py`). The target CORS policy adds `PATCH`, `DELETE`, `Authorization`, `Idempotency-Key`, `If-Match`, `If-None-Match`, `X-Org-ID`, `X-Request-ID`, `Prefer`, and exposes `Location`, `ETag`, `Retry-After`, `Idempotent-Replayed`.

### 2.1 Compatibility commitments for existing routes

| Commitment | Detail |
|---|---|
| C1. No route is removed or renamed within `/api/v1` | Routes 1–26 stay. Superseding routes are added alongside. Removal happens only under the §7 deprecation policy. |
| C2. Response fields are only added, never removed or retyped | Example: `ProjectResponse` gains `production_mode`; `SceneResponse` gains `screenplay_version_id`, `superseded_in_version`, `organization_id`. |
| C3. Canonical list routes keep returning all rows by default | `GET /scenes` and `/entities` add an opt-in `?current=true` (rows where `superseded_in_version IS NULL`). The default flips only through the deprecation policy, because the UI currently shows all generations. |
| C4. `sync_execution` | Phase 1: the UI and tests send `sync_execution=false` explicitly and poll route 16. Phase 2: the server default becomes `false` (announced breaking-behaviour change with a `Deprecation` header on requests that omit the field for one release). Phase 3: `sync_execution=true` is accepted only when `environment=test`; otherwise `422`. |
| C5. `POST /approvals/{id}/decide` | The response shape is kept. Clients may send `Prefer: respond-async` to get `202` + `Location` to the run (target behaviour, LLD §7). The synchronous mode stays the default until the UI migrates. Legacy `approved_*_ids` fields stay accepted and map into `selection`. An unknown scope returns `422` (fixes SEC-08; strictly a bug fix). |
| C6. Error bodies | Today: `{"detail", "error"}`. Target problem+json **keeps both keys** (§5), so existing UI parsing (`apps/ui/api_client.py`) keeps working. |
| C7. Identity header | `X-Actor-ID` stays valid in `test` only after the DEC-002 switch. Before the switch it works as today, but the dev fallback must be opt-in (`ALLOW_DEV_IDENTITY_FALLBACK=true`), not driven by an `environment` default (SEC-02). |
| C8. Manual canonical writes (routes 19, 21, 26) | They keep their shape but require capability `research.write_canon` / `film_bible.write_canon`, write a project version and audit, and validate foreign IDs. Phase C adds a candidate-path alternative (`POST …/research/claim-candidates`). |
| C9. Status codes | Route 10 keeps `200`. New upload routes use `201`/`202`. `TenantAccessViolation` changes from 403 to **404** (the route still fails; only the code changes; documented in the release notes). |

---

## 3. Authentication and authorization model

**Role templates** are seeded in `role_templates` and can be customised per org: `org_owner`, `org_admin`, `management`, `director`, `writer`, `researcher`, `art_department`, `cinematographer`, `continuity_supervisor`, `production_coordinator`, `legal_consent_officer`, `viewer`.

**Capabilities** (keys in `capabilities`):

| Capability | Typical holders |
|---|---|
| `project.read`, `project.create`, `project.update`, `project.archive` | members / org_admin / director |
| `member.manage` | org_owner, org_admin |
| `asset.upload`, `asset.read`, `likeness.view` | members; `likeness.view` only for legal_consent_officer + director when consent is active |
| `screenplay.edit`, `screenplay.submit`, **`screenplay.lock`** | writer/director; **management only** for lock |
| `workflow.run.<WF-nn>` | role-dependent, e.g. researcher → WF-02 |
| `approval.decide.creative`, `approval.decide.management`, `approval.decide.cost`, `approval.decide.consent` | director; management; production_coordinator (cost, by limit); legal_consent_officer |
| `continuity.decide` | director, continuity_supervisor |
| `consent.record`, `consent.verify`, `consent.revoke` | legal_consent_officer (the verifier must differ from the recorder) |
| `package.compile`, `package.export`, `generation.submit`, `import.create` | director, production_coordinator |
| `provider.connect` | org_admin |
| `research.write_canon`, `film_bible.write_canon` | director (legacy direct-write path) |

---

## 4. Target REST resources per module
**Legend:**
- **202** = async (returns a run or job resource)
- **IK** = `Idempotency-Key` honoured or required
- **P** = cursor-paginated

| Module | Method + path | Capability | Flags |
|---|---|---|---|
| iam/authz | `GET /me` (user, memberships, capabilities) | authenticated | |
| | `GET/POST /org/members`, `PATCH /org/members/{id}` | `member.manage` | P, IK |
| | `GET/PUT /projects/{pid}/members/{user_id}` | `member.manage` | |
| projects | `PATCH /projects/{pid}` (production_format, production_mode, delivery_profile) | `project.update` | If-Match |
| | `POST /projects/{pid}/archive` | `project.archive` | IK |
| assets | `POST /projects/{pid}/uploads` → presigned PUT | `asset.upload` | IK |
| | `POST /uploads/{id}/complete` | `asset.upload` | 202 |
| | `GET /projects/{pid}/assets?classification=&status=` | `asset.read` | P |
| | `GET /assets/{id}`, `GET /assets/{id}/download` (302 → signed URL), `GET /assets/{id}/derivatives`, `GET /assets/{id}/lineage` | `asset.read` (+ `likeness.view` + consent for restricted) | |
| screenplay | `POST /projects/{pid}/screenplay-versions` (from asset, or child of a parent) | `screenplay.edit` | IK |
| | `GET /projects/{pid}/screenplay-versions`, `GET /screenplay-versions/{id}`, `GET /screenplay-versions/{id}/changes` | `project.read` | P |
| | `POST /screenplay-versions/{id}/submit` (creates a management approval) | `screenplay.submit` | IK |
| | `POST /screenplay-versions/{id}/lock` (decides the management approval; §8.1) | `screenplay.lock` | IK |
| | `GET /projects/{pid}/screenplay-suggestions`, `POST /screenplay-suggestions/{id}/accept-into-revision`, `POST …/reject` | `screenplay.edit` | P, IK |
| | `GET /impact-analyses/{id}`, `POST /creative-decisions` | `project.read` / `approval.decide.creative` | IK |
| story / shots | `GET /projects/{pid}/scenes?current=true&screenplay_version_id=` | `project.read` | P |
| | `GET/POST /projects/{pid}/sequences`, `GET/POST /sequences/{id}/shots`, `GET /shots/{id}`, `PATCH /shots/{id}` (creates a new shot version) | `project.read` / `shot.edit` | P, IK, If-Match |
| research | existing routes + `GET /research/claims/{id}/evidence`, `GET/POST /projects/{pid}/timeline-events` | `project.read` / `research.write` | P |
| characters / world / cinematography | `GET/POST /projects/{pid}/characters`, `/characters/{id}/versions`, `/physical-profile`, `/measurements`, `/states`; `/locations`, `/costumes`, `/props`; `/cinematography-profile`, `/camera-profiles`, `/lens-profiles`, `/lighting-profiles`; `/capture-plans`, `/capture-manifests` | per-module `*.read` / `*.edit` | P, IK |
| digital humans / consent | `POST /performers`; `POST /performers/{id}/consents` (§8.6); `POST /consents/{id}/verify`; `POST /consents/{id}/revoke`; `POST /consent-checks` (dry-run of the gate) | `consent.record` / `consent.verify` / `consent.revoke` | IK |
| | `GET/POST /projects/{pid}/digital-humans`, `/digital-humans/{id}/avatar-versions`, `/voice-profiles` | `dh.edit` (+ the gate) | IK |
| continuity | `GET /projects/{pid}/continuity/findings?status=`, `POST /continuity/findings/{id}/decisions`, `GET/POST /projects/{pid}/continuity/rules` | `project.read` / `continuity.decide` | P, IK |
| ai orchestration | `POST /projects/{pid}/workflow-runs` `{workflow: "WF-06", inputs: {...}}` | `workflow.run.<WF>` | **202**, IK |
| | `GET /workflow-runs/{id}`, `POST /workflow-runs/{id}/cancel`, `GET /projects/{pid}/workflow-runs` | `project.read` / same as start | P |
| approvals | `GET /projects/{pid}/approvals?status=pending&level=`, `GET /me/approvals` (inbox), `POST /approvals/{id}/decide` | `approval.decide.<level>` | P, IK, 202 (Prefer) |
| providers | `GET /providers`, `GET /providers/{id}/capability-snapshots` | `project.read` | P |
| | `POST /org/provider-connections`, `POST /provider-connections/{id}/validate` | `provider.connect` | IK |
| generation | `POST /shots/{id}/packages` (runs WF-09) | `package.compile` | **202**, IK |
| | `GET /packages/{id}`, `POST /packages/{id}/submit-for-approval` | `project.read` / `package.compile` | IK |
| | `POST /packages/{id}/exports` (§8.3), `GET /exports/{id}`, `GET /exports/{id}/download` | `package.export` | **202**, IK |
| | `POST /packages/{id}/generation-jobs` (§8.5), `POST /generation-jobs/{id}/cancel`, `POST /generation-jobs/{id}/convert-to-manual`, `POST /generation-jobs/{id}/reconcile` (operator) | `generation.submit` | **202**, IK |
| | `POST /packages/{id}/imports` (§8.4), `POST /imports/{id}/complete`, `POST /imports/{id}/mapping` | `import.create` | 202, IK |
| | `POST /imports/{id}/reviews`, `POST /output-reviews/{id}/revision-requests` | `approval.decide.creative` | IK |
| handoff (V1 manual) | `POST /projects/{pid}/handoff-manifests` `{format: "json"|"csv", scope}` | `package.export` | 202, IK |
| integrations | `POST /webhooks/providers/{provider_key}/{connection_id}` | signature (§6) | — |
| analytics | `GET /projects/{pid}/usage`, `GET /org/usage` | `project.read` / `org_admin` | P |

Post-production handoff manifests contain exactly the Master Prompt §14 fields: approved footage, shot identifiers, scene and sequence relationships, version numbers, frame rates, resolution, aspect ratios, timecodes where available, audio references, dialogue versions, continuity notes, asset manifests and source provenance. Only `json` and `csv` are offered until another format has been validated in a target editor (DEC-014).

---

## 5. Errors: RFC 9457 problem details
These are produced by `apps/api/errors.py::_domain_error_handler`, which keeps its single mapping table (`_STATUS_BY_ERROR`) extended with the LLD §6 taxonomy.

```json
{
  "type": "urn:tattva:problem:consent-required",
  "title": "Consent required",
  "status": 409,
  "detail": "Performer 'p-81…' has no active consent for purpose 'performance_transformation' on this project.",
  "instance": "/api/v1/packages/7c1e…/exports",
  "error": "ConsentRequiredError",
  "correlation_id": "req_01JC9…",
  "errors": [
    {"code": "consent_missing", "performer_id": "p-81…", "purpose": "performance_transformation"}
  ]
}
```

| Current (`errors.py`) | HTTP | Problem `type` suffix |
|---|---|---|
| `AuthenticationError` | 401 (+ `WWW-Authenticate: Bearer`) | `unauthenticated` |
| `TenantAccessViolation` | 403 → **404** (C9) | `not-found` |
| `NotFoundError` | 404 | `not-found` |
| `VersionConflictError` | 409 | `version-conflict` |
| `InvalidStateError` | 409 | `invalid-state` |
| `PayloadTooLargeError` | 413 | `payload-too-large` |
| `UnsupportedMediaTypeError` | 415 | `unsupported-media-type` |
| `ValidationFailure` | 422 | `validation` |
| FastAPI `RequestValidationError` | 422 | `validation` (pydantic errors in `errors[]`) |
| `DomainInvariantError` (fallback) | 409 | `conflict` |
| Unhandled | 500 | `internal` (no detail leakage) |
| *new* `AuthorizationError` / `ScreenplayLockedError` / `ConsentRequiredError` / `ApprovalRequiredError` / `IdempotencyKeyReuseError` / `RateLimitedError` / `DependencyUnavailableError` | 403 / 409 / 409 / 409 / 422 / 429 / 503 | `forbidden` / `screenplay-locked` / `consent-required` / `approval-required` / `idempotency-key-reuse` / `rate-limited` / `dependency-unavailable` |

---

## 6. Webhook ingestion
`POST /api/v1/webhooks/providers/{provider_key}/{connection_id}`

1. Read the **raw body** (≤ 1 MB) before any JSON parsing.
2. Resolve the `provider_connections` row and its adapter. Unknown or disabled connections get `404`, with nothing logged beyond a counter.
3. Call `adapter.verify_webhook(headers, raw_body, secret_ref)`. The adapter implements **only the scheme the provider documents**, recorded in its capability snapshot's `verification_notes`. No scheme is assumed. A provider without documented signing gets **no webhook route**: Tattva polls it instead.
4. Enforce the timestamp-tolerance and replay window when the scheme provides a timestamp. De-duplicate on `UNIQUE (connection_id, provider_event_id)` in `external_execution_logs`.
5. Persist the redacted payload with `signature_valid`, enqueue `generation.poll` for the referenced attempt (`dedupe_key = poll:{attempt_id}:{provider_event_id}`), and return `204` quickly.
6. **A webhook never changes job state directly.** The poll task confirms state through the provider's status API, which protects against forged-but-valid-looking payloads and out-of-order delivery.

Invalid signatures get `401`. The response does not differ by failure reason, and the event is counted for alerting.

---

## 7. API versioning and deprecation policy
1. **Additive changes** (new routes, new optional request fields, new response fields, new enum values in *response* fields) ship within `/api/v1`. Clients must ignore unknown fields and treat unknown enum values as "other".
2. **Breaking changes** (removing or renaming a field or route, changing a type, making an optional field required, changing a default with semantic effect, tightening validation on existing inputs) need one of:
   - a new route alongside the old one, or
   - `/api/v2` for wholesale changes. Not foreseen in FD-V1.
3. **Deprecation:** deprecated routes and fields return `Deprecation: @<unix-ts>` (RFC 9745) and `Sunset: <http-date>` (RFC 8594), plus `Link: <successor>; rel="successor-version"`. The minimum window is **two releases and 90 days**. While Streamlit is the only client, the window may shorten to one release when the UI has already migrated, but only with that approval recorded in the ADR register.
4. Each deprecation is recorded in `docs/engineering/ADR_REGISTER.md` and in the release notes. A contract test (`tests/api/test_contract_snapshot.py`, new) snapshots the OpenAPI schema and fails on unannounced breaking diffs.
5. **Events** carry `event_version`. Consumers must ignore unknown fields. A breaking payload change publishes a new `event_version` in parallel for one release.

---

## 8. Concrete request and response examples

### 8.1 Screenplay lock (management)
```http
POST /api/v1/screenplay-versions/sv_3f2a…/lock
Authorization: Bearer eyJ…
Idempotency-Key: 8e0b6a1e-2b9c-4c55-9a51-1f3f0e2d7c11
Content-Type: application/json

{
  "approval_request_id": "apr_91c0…",
  "decision": "approved",
  "notes": "Locked for production after legal read-through.",
  "acknowledged_impact_analysis_id": "ia_5d10…"
}
```
```json
HTTP/1.1 200 OK
{
  "id": "sv_3f2a…",
  "project_id": "prj_77a1…",
  "version_number": 2,
  "parent_version_id": "sv_1b02…",
  "status": "approved_locked",
  "is_production_canonical": true,
  "content_sha256": "4be1…c9",
  "locked_by": "usr_mgmt_02…",
  "locked_at": "2026-11-05T10:14:22Z",
  "lock_approval_id": "apr_91c0…",
  "superseded_version_id": "sv_1b02…",
  "impact_analysis": {"id": "ia_5d10…", "status": "completed", "flagged_items": 14},
  "project_version": 9
}
```
If the actor lacks `screenplay.lock`, the response is `403 forbidden`. If the version is not `in_review`, it is `409 invalid-state`. Edits to a locked version (`PATCH`) return `409 screenplay-locked`.

### 8.2 Shot specification (`GET /api/v1/shots/{id}`)
```json
{
  "id": "sh_0c4e…",
  "project_id": "prj_77a1…",
  "shot_code": "SQ03-SC12-SH004",
  "version": 3,
  "status": "approved",
  "sequence_id": "seq_12…",
  "scene_id": "scn_9a…",
  "screenplay_version_id": "sv_3f2a…",
  "production_mode": null,
  "effective_production_mode": "hybrid_live_action",
  "production_method": "performance_transformation",
  "duration_s": 6.5,
  "subjects": [
    {"type": "character", "id": "chr_ashoka…", "character_version_id": "cv_4…", "state_id": "cst_post_battle…"},
    {"type": "costume", "id": "cos_armour…", "state_id": "coss_bloodied…"},
    {"type": "prop", "id": "prp_sword…", "state_id": null},
    {"type": "location", "id": "loc_dhauli…", "environment_state_id": "env_dusk_smoke…"}
  ],
  "camera_spec": {
    "schema_version": "1.0",
    "spec_kind": "physical",
    "metadata_origin": "creative_target",
    "physical": {
      "sensor_format": "super35",
      "recording_resolution": "4096x2160",
      "frame_rate": 24,
      "shutter_angle": 180,
      "iso_ei": 800,
      "aperture": "T2.8",
      "white_balance_k": 4300,
      "focal_length_mm": 40,
      "lens_characteristics": "anamorphic-look flare, mild breathing",
      "camera_distance_m": 3.0,
      "camera_height_m": 1.2,
      "camera_angle": "low",
      "framing": "medium_wide",
      "focus_distance_m": 3.0,
      "depth_of_field": "shallow",
      "camera_movement": "slow push-in",
      "rig_or_stabilization": "dolly",
      "aspect_ratio": "2.39:1"
    },
    "virtual": null,
    "camera_profile_id": "cam_pkg_a…",
    "lens_profile_id": "lens_set_b…",
    "lighting_profile_id": "lgt_dusk_smoke…",
    "recommendation": null,
    "extensions": {}
  },
  "continuity_status": "approved_canon",
  "provenance": {"source": "WF-06", "status": "approved", "confidence": 0.82, "approved_by": "usr_dir_01…", "version": 3}
}
```

### 8.3 Package export (manual)
```http
POST /api/v1/packages/pkg_7c1e…/exports
Authorization: Bearer eyJ…
Idempotency-Key: 0d3b9f0c-6a6a-4a7e-8a51-3b1ce5a2a001
Content-Type: application/json

{"format": "zip", "include": ["manifest_json", "instructions_md", "reference_bundle"], "manual_target_name": "Runway web app"}
```
```json
HTTP/1.1 202 Accepted
Location: /api/v1/exports/exp_51aa…
{
  "id": "exp_51aa…",
  "package_id": "pkg_7c1e…",
  "package_version": 2,
  "package_content_sha256": "a91f…07",
  "status": "building",
  "execution_mode": "manual",
  "manual_target_name": "Runway web app",
  "consent_check": {"result": "pass", "checked_at": "2026-11-05T10:20:03Z", "purposes": ["performance_transformation"]},
  "warnings": [
    "Confirm you have authority to submit these references to the selected external tool; its content licence and visibility terms apply."
  ],
  "exported_by": "usr_dir_01…",
  "created_at": "2026-11-05T10:20:03Z"
}
```
The finished export (`GET /exports/exp_51aa…`) reports `status: "ready"`, `bundle_asset_id` and `download_url_expires_in_s: 900`. The JSON manifest inside the bundle follows the Gap §7.5 envelope: package, project and shot IDs and versions; execution mode; capability snapshot (null for manual); prompt; camera spec; reference manifest with asset ID, checksum, role and rights status; context package hash; approval IDs; content hash. It contains **no secrets**.

### 8.4 Manual import
```http
POST /api/v1/packages/pkg_7c1e…/imports
Authorization: Bearer eyJ…
Idempotency-Key: 5f7a0a42-1d0b-4b1f-9a1e-6b0b3a7c9d10
Content-Type: application/json

{
  "mode": "manual",
  "external_tool_name": "Runway web app",
  "operator_notes": "Take 2 chosen; seed unknown.",
  "files": [
    {"client_file_id": "f1", "filename": "sh004_take1.mp4", "size_bytes": 48211934, "declared_mime": "video/mp4"},
    {"client_file_id": "f2", "filename": "sh004_take2.mp4", "size_bytes": 50110022, "declared_mime": "video/mp4"}
  ]
}
```
```json
HTTP/1.1 201 Created
Location: /api/v1/imports/imp_2e9d…
{
  "id": "imp_2e9d…",
  "package_id": "pkg_7c1e…",
  "mode": "manual",
  "status": "uploading",
  "files": [
    {"client_file_id": "f1", "asset_id": "ast_a1…", "upload": {"method": "PUT", "url": "https://<bucket-endpoint>/…signed…", "expires_in_s": 900, "headers": {"Content-Type": "video/mp4"}}},
    {"client_file_id": "f2", "asset_id": "ast_a2…", "upload": {"method": "PUT", "url": "https://<bucket-endpoint>/…signed…", "expires_in_s": 900, "headers": {"Content-Type": "video/mp4"}}}
  ]
}
```
After `POST /imports/imp_2e9d…/complete` (202), each file is quarantined, sniffed and scanned. Then `POST /imports/imp_2e9d…/mapping` sends:

```json
{"mappings": [{"asset_id": "ast_a2…", "shot_id": "sh_0c4e…", "role": "shot_output_candidate"}],
 "discard_asset_ids": ["ast_a1…"]}
```
That call returns `200 {"status": "mapped", "inspection_run_id": "wr_…"}` and starts WF-11.

### 8.5 Generation job (connected; FD-V2)
```http
POST /api/v1/packages/pkg_7c1e…/generation-jobs
Authorization: Bearer eyJ…
Idempotency-Key: c3c1d6a9-1c87-4a0b-8a2d-0f4b3d9e7e55
Content-Type: application/json

{"provider_connection_id": "pcn_19…", "capability_snapshot_id": "pcs_88…", "max_cost": {"amount": 12.0, "unit": "credits"}}
```
```json
HTTP/1.1 202 Accepted
Location: /api/v1/generation-jobs/gj_40b2…
{
  "id": "gj_40b2…",
  "package_id": "pkg_7c1e…",
  "status": "awaiting_authorization",
  "execution_mode": "connected_api",
  "provider": {"key": "<verified-provider-key>", "capability_snapshot_id": "pcs_88…", "last_verified_at": "2026-10-28"},
  "cost_estimate": {"amount": 9.5, "unit": "credits", "basis": "capability snapshot cost_model"},
  "approvals": [
    {"id": "apr_c1…", "level": "creative", "status": "decided", "decision": "approved"},
    {"id": "apr_c2…", "level": "cost", "status": "pending", "required_capability": "approval.decide.cost"}
  ],
  "attempts": [],
  "can_convert_to_manual": true
}
```
Later, `GET /generation-jobs/gj_40b2…` may show `"status": "unknown_outcome"` with `attempts[0].status = "unknown_outcome"` and `"next_action": "reconciling"` (LLD §2.6). The provider key and endpoints shown come only from a verified snapshot. None are assumed here.

### 8.6 Consent record
```http
POST /api/v1/performers/prf_51…/consents
Authorization: Bearer eyJ…
Idempotency-Key: 9a8f1f5e-7b5d-4d8f-b3d3-2c1e0f9a6b77
Content-Type: application/json

{
  "project_id": "prj_77a1…",
  "purposes": ["digital_double", "performance_transformation", "production_audio_use"],
  "scope": {"media": ["film", "trailer"], "territories": ["worldwide"], "providers_allowed": "any_verified"},
  "valid_from": "2026-11-10T00:00:00Z",
  "valid_until": "2027-12-31T23:59:59Z",
  "document_asset_id": "ast_consent_pdf…",
  "revocation_terms": "Revocable per clause 9 of the performer agreement; delivered cuts unaffected.",
  "notes": "Voice cloning explicitly excluded."
}
```
```json
HTTP/1.1 201 Created
{
  "id": "cns_c0…",
  "performer_id": "prf_51…",
  "project_id": "prj_77a1…",
  "version": 1,
  "supersedes_id": null,
  "status": "pending_verification",
  "purposes": ["digital_double", "performance_transformation", "production_audio_use"],
  "valid_from": "2026-11-10T00:00:00Z",
  "valid_until": "2027-12-31T23:59:59Z",
  "recorded_by": "usr_legal_01…",
  "verified_by": null,
  "sensitivity": "restricted",
  "next_step": "POST /api/v1/consents/cns_c0…/verify by a different user holding consent.verify"
}
```
The consent is not `active` until verified by a second person. `voice_clone` is absent from `purposes`, so any package that requires a cloned voice for this performer fails validation with `consent_missing`.

---

## 9. Domain events (outbox-published)
Events are rows in `outbox_tasks` with `queue='events'`, `task_type='domain_event'` and the payload equal to the envelope below. They are inserted **in the same transaction** as the state change. The `events` pool dispatches them to in-process handlers (notifications, impact analysis, consent invalidation, usage). In V1 there is no external broker and no customer-facing webhooks.

### 9.1 Envelope JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:tattva:schema:event-envelope:1",
  "type": "object",
  "required": ["event_id", "event_type", "event_version", "occurred_at", "organization_id", "actor", "subject", "data"],
  "properties": {
    "event_id": {"type": "string", "format": "uuid"},
    "event_type": {"type": "string", "pattern": "^[a-z_]+\\.[a-z_]+$"},
    "event_version": {"type": "integer", "minimum": 1},
    "occurred_at": {"type": "string", "format": "date-time"},
    "organization_id": {"type": "string"},
    "project_id": {"type": ["string", "null"]},
    "actor": {
      "type": "object",
      "required": ["kind"],
      "properties": {"kind": {"enum": ["human", "system"]}, "user_id": {"type": ["string", "null"]}}
    },
    "correlation_id": {"type": ["string", "null"]},
    "causation_id": {"type": ["string", "null"], "description": "event_id or request id that caused this"},
    "subject": {
      "type": "object",
      "required": ["type", "id"],
      "properties": {"type": {"type": "string"}, "id": {"type": "string"}, "version": {"type": ["integer", "null"]}}
    },
    "data": {"type": "object"}
  },
  "additionalProperties": false
}
```
**Rule:** `data` carries IDs, statuses and hashes, **never** restricted content: no likeness, no screenplay text, no consent document body.

### 9.2 Key events
Each `data` object is listed with its minimal schema (`required` fields) followed by an example.

| Event type | Producer | Main consumers |
|---|---|---|
| `workflow_run.status_changed` | ai_orchestration | UI notifications, usage |
| `approval.requested` / `approval.decided` | approvals | notifications (approver inbox), resume dispatcher |
| `project_version.committed` | versioning | cache/ETag, analytics |
| `screenplay_version.locked` | screenplay | impact analysis, packages (invalidate non-canonical) |
| `screenplay_version.impact_analyzed` | screenplay | notifications, continuity |
| `asset.available` / `asset.rejected` | assets | import jobs, WF-01 input readiness |
| `consent.activated` / `consent.revoked` / `consent.expired` | digital_humans | packages, generation, assets, notifications |
| `production_package.approved` / `production_package.exported` / `production_package.invalidated` | generation | notifications, audit analytics |
| `generation_job.status_changed` / `generation_attempt.unknown_outcome` | generation | notifications, ops alerting, cost |
| `import_job.mapped` | generation | WF-11 trigger |
| `continuity_finding.raised` | continuity | notifications, shot status |
| `output_review.decided` | generation | versioning, revision requests |

**`approval.decided`** (data required: `approval_level`, `decision`, `target_type`, `target_id`):
```json
{
  "event_id": "1b6c…", "event_type": "approval.decided", "event_version": 1,
  "occurred_at": "2026-11-05T10:14:22Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "human", "user_id": "usr_mgmt_02…"}, "correlation_id": "req_01JC9…", "causation_id": null,
  "subject": {"type": "approval_request", "id": "apr_91c0…", "version": null},
  "data": {"approval_level": "management", "decision": "approved", "target_type": "screenplay_version",
           "target_id": "sv_3f2a…", "workflow_run_id": null, "selection": null}
}
```

**`screenplay_version.locked`** (required: `version_number`, `superseded_version_id`, `content_sha256`):
```json
{
  "event_id": "2c7d…", "event_type": "screenplay_version.locked", "event_version": 1,
  "occurred_at": "2026-11-05T10:14:22Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "human", "user_id": "usr_mgmt_02…"}, "correlation_id": "req_01JC9…", "causation_id": "1b6c…",
  "subject": {"type": "screenplay_version", "id": "sv_3f2a…", "version": 2},
  "data": {"version_number": 2, "superseded_version_id": "sv_1b02…", "content_sha256": "4be1…c9", "project_version": 9}
}
```

**`workflow_run.status_changed`** (required: `workflow_key`, `from_status`, `to_status`):
```json
{
  "event_id": "3d8e…", "event_type": "workflow_run.status_changed", "event_version": 1,
  "occurred_at": "2026-11-05T09:58:10Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "system", "user_id": null}, "correlation_id": "req_01JC7…", "causation_id": null,
  "subject": {"type": "workflow_run", "id": "wr_6a…", "version": null},
  "data": {"workflow_key": "WF-01", "from_status": "running", "to_status": "awaiting_approval",
           "approval_request_id": "apr_55…", "generator_mode": "deterministic", "error_class": null}
}
```

**`consent.revoked`** (required: `performer_id`, `purposes`, `project_id`, `effective_at`):
```json
{
  "event_id": "4e9f…", "event_type": "consent.revoked", "event_version": 1,
  "occurred_at": "2026-11-05T11:02:00Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "human", "user_id": "usr_legal_01…"}, "correlation_id": "req_01JCB…", "causation_id": null,
  "subject": {"type": "performer_consent", "id": "cns_c0…", "version": 1},
  "data": {"performer_id": "prf_51…", "purposes": ["digital_double", "performance_transformation"],
           "project_id": "prj_77a1…", "effective_at": "2026-11-05T11:02:00Z"}
}
```
Handlers: invalidate unsubmitted packages, cancel queued jobs, flag submitted attempts and the affected assets, and notify (HLD §4.5).

**`production_package.exported`** (required: `package_version`, `content_sha256`, `execution_mode`, `export_id`):
```json
{
  "event_id": "5fa0…", "event_type": "production_package.exported", "event_version": 1,
  "occurred_at": "2026-11-05T10:20:41Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "human", "user_id": "usr_dir_01…"}, "correlation_id": "req_01JCA…", "causation_id": null,
  "subject": {"type": "production_package", "id": "pkg_7c1e…", "version": 2},
  "data": {"package_version": 2, "content_sha256": "a91f…07", "execution_mode": "manual",
           "export_id": "exp_51aa…", "manual_target_name": "Runway web app", "shot_id": "sh_0c4e…"}
}
```

**`generation_attempt.unknown_outcome`** (required: `job_id`, `attempt_number`, `client_reference`, `connection_id`):
```json
{
  "event_id": "6ab1…", "event_type": "generation_attempt.unknown_outcome", "event_version": 1,
  "occurred_at": "2026-11-05T12:00:31Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "system", "user_id": null}, "correlation_id": null, "causation_id": "…",
  "subject": {"type": "generation_attempt", "id": "ga_1…", "version": null},
  "data": {"job_id": "gj_40b2…", "attempt_number": 1, "client_reference": "c0d1…", "connection_id": "pcn_19…",
           "sent_at": "2026-11-05T11:59:01Z", "reconciliation": "lookup_supported"}
}
```

**`import_job.mapped`** (required: `package_id`, `asset_ids`, `shot_ids`):
```json
{
  "event_id": "7bc2…", "event_type": "import_job.mapped", "event_version": 1,
  "occurred_at": "2026-11-05T13:11:00Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "human", "user_id": "usr_dir_01…"}, "correlation_id": "req_01JCC…", "causation_id": null,
  "subject": {"type": "import_job", "id": "imp_2e9d…", "version": null},
  "data": {"package_id": "pkg_7c1e…", "mode": "manual", "asset_ids": ["ast_a2…"], "shot_ids": ["sh_0c4e…"]}
}
```

**`continuity_finding.raised`** (required: `dimension`, `severity`, `subject_type`, `subject_id`):
```json
{
  "event_id": "8cd3…", "event_type": "continuity_finding.raised", "event_version": 1,
  "occurred_at": "2026-11-05T13:20:00Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "system", "user_id": null}, "correlation_id": null, "causation_id": "7bc2…",
  "subject": {"type": "continuity_finding", "id": "cf_9…", "version": null},
  "data": {"dimension": "costume", "attribute": "armour", "severity": "high", "subject_type": "shot",
           "subject_id": "sh_0c4e…", "rule_id": "cr_3…", "asset_id": "ast_a2…", "status": "conflict_detected"}
}
```

**`project_version.committed`** (required: `version_number`, `source`):
```json
{
  "event_id": "9de4…", "event_type": "project_version.committed", "event_version": 1,
  "occurred_at": "2026-11-05T10:14:22Z", "organization_id": "org_…", "project_id": "prj_77a1…",
  "actor": {"kind": "human", "user_id": "usr_mgmt_02…"}, "correlation_id": "req_01JC9…", "causation_id": "2c7d…",
  "subject": {"type": "project_version", "id": "pv_…", "version": 9},
  "data": {"version_number": 9, "source": {"type": "screenplay_version", "id": "sv_3f2a…"}, "refs": {"screenplay_version_id": "sv_3f2a…"}}
}
```

### 9.3 Delivery semantics
- **At-least-once.** Handlers are idempotent and keyed by `event_id`: each handler records processed IDs in its own state or uses natural unique keys.
- **Ordering** is guaranteed only per `subject.id`. The dispatcher processes events for the same subject in `occurred_at` order, using `dedupe_key=evt:{subject.id}:{seq}` and per-subject serialisation via `pg_advisory_xact_lock(hashtext(subject_id))`.
- **Retention** follows `outbox_tasks` completed rows (30 days). `audit_events` remains the permanent record.
