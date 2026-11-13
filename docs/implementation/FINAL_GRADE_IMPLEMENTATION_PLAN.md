# Final-Grade Implementation Plan — Tattva AI Film Director

**Doc ID:** TFD-ENG-002 · **Version:** 1.0 · **Date:** 2026-11-06 · **Status:** APPROVED 2026-11-06, with an amendment: React replaces Streamlit now (ADR-002). In execution.

**Inputs:**
- `docs/audit/00–11`, with the gate decisions in `11`.
- `docs/product/PRD_v1.0.md` and `PRODUCT_ROADMAP.md`.
- `docs/architecture/*`, `docs/engineering/*` and ADR-002…008.
- Guided Workspace UX Strategy v1.0 and Wireframe v1.1 (`docs/product/ux/guided-workspace-v1.0/`).

---

## 1. Goal

Take the current foundation through FD-V1 and then FD-V2:
- **Current:** 3 working deterministic slices and 1 broken slice, header identity, and 8 Streamlit views.
- **FD-V1:** an approved filmmaking and production blueprint, delivered through the **10-section Guided Workspace**, with manual tool handoff.
- **FD-V2:** connected and manual generation, plus output inspection.

The work is done as small, verified, reversible increments. Nothing is rebuilt from scratch.

## 2. Working rules (apply to every milestone)

1. **Branches.**
   - This audit and design work is committed on `docs/product-evolution-audit`.
   - Implementation happens on `feat/<milestone>` branches cut from it.
   - `main` changes only when you ask me to merge or open a PR.
2. **One milestone is one or more reviewable commits**, each with tests. The suite stays green at every commit, from the C1 fix onward.
3. **Migrations are additive only:** expand → backfill → verify → switch → contract.
   - Each migration must pass an upgrade/downgrade round-trip test.
   - No applied revision is ever edited.
   - No DB reset. `pg_dump` runs before any shared-environment migration.
4. **No fake success.** Deterministic and mock generators carry a label in the API and UI. Provider states are honest.
5. **Existing behaviour is protected.** Current routes stay compatible (C1–C9 in `API_AND_EVENT_CONTRACTS.md`), and the G-01, G-02 and G-03 tests must keep passing.
6. **Definition of Done** is Master Prompt §29, using the checklist in `ACCEPTANCE_CRITERIA.md`. A screen is not a feature.
7. **Status reports** after each milestone cover what changed, real test output, what is still mocked, and what comes next.

## 3. Sequence overview

```mermaid
flowchart LR
  S0[S0 Housekeeping] --> C1[C1 Fix G-04] --> C2[C2 Test DB + CI] --> C3[C3 Auth] --> C45[C4/C5 RBAC + tenant integrity]
  C45 --> C6[C6 Async + worker hardening] --> GW[GW Guided Workspace foundation]
  GW --> C7[C7 Media + MinIO] --> C8[C8 Approvals + audit] --> C9[C9 Observability + containers] --> C10[C10 ModelGateway]
  C10 --> D[D1 to D12: FD-V1 sections 01 to 10] --> F1[F1 FD-V1 pilot gate] --> E[E0 to E9: FD-V2] --> F2[F2 Production readiness]
```

The Guided Workspace shell (GW) comes right after auth, roles and async, so every later feature lands inside the final navigation rather than the old 8-view prototype.

## 4. Stage S0 — Housekeeping (S)

| Item | Detail |
|---|---|
| S0.1 | Commit `docs/` (audit, design docs, UX package, decisions) on `docs/product-evolution-audit`. |
| S0.2 | Bump `INFORMATION_ARCHITECTURE.md` to v1.1. The 10 journey sections become primary navigation, and the 60 canonical screens and the 36 wireframe screens are mapped beneath them as Studio Tools. No capability is removed. |
| S0.3 | Add a **Journey manifest** spec (`docs/product/JOURNEY_MANIFEST.md` plus a machine-readable `packages/domain/journey_manifest.yaml`). It defines sections 01–10, accordions and subpoints with stable `JRN-` IDs, required/optional flags, applicability rules (by mode, format and role), completion rules, linked TFD requirements and the Studio Tool for each step. |

**Exit:** docs committed and the manifest reviewed.

## 5. Stage C — Foundation hardening

| # | Milestone | Scope | Key files | Tests / exit criteria | Size |
|---|---|---|---|---|---|
| **C1** | Fix G-04 forward | See below | `workflows/film_bible_synthesis/*`, `services/film_bible*.py`, `tests/support.py` | All 6 G-04 tests pass; new regression tests for A, B, C, H and I; **full suite green** | S |
| **C2** | Test DB isolation + CI | See below | `tests/conftest.py`, `.github/workflows/ci.yml`, `pyproject.toml` | Tests never touch the dev DB. CI green. Mypy runs (errors burned down per package) | M |
| **C3** | Authentication | See below | `apps/api/dependencies.py`, `services/identity.py` → `packages/iam/`, `core/config.py`, `apps/ui/api_client.py` | Authn negative tests. A forged or absent token gives 401 outside `test`. G-01…G-04 tests pass with tokens | M |
| **C4/C5** | RBAC + tenant integrity + version safety | See below | new `packages/iam/policy.py`, repositories, `*_review.py`, migrations R-04…R-07 | Negative authZ matrix for every router. Cross-tenant ID tests. Concurrent-approval test gives unique versions | L |
| **C6** | Async-by-default + worker hardening | **Backend done, 2026-11-06.** See below | `apps/worker`, `outbox_tasks` migration, services | Lease reclaim, retry/backoff, dead-letter and checkpoint-resume all covered by tests (no live kill-worker drill; the lease-expiry path is tested by directly expiring a lease, which is equivalent). Retries respect `max_attempts`. **UI task tray deferred to GW2** (no frontend exists yet to show one in; `sync_execution=True` keeps the old Streamlit screens working synchronously in the meantime). | L |

**C1 scope:**
- Declare `approved_rule_ids` and `decision_notes` in state.
- Switch the claims call to `list_claims`.
- Purge the film-bible tables in teardown.
- Stop the version-field overwrite and preserve the initiator `actor_id`.
- Add the pending-status guard.
- Validate category and strictness against the enums.
- Commit together with the user's WIP.

**C2 scope:**
- A per-session `tattva_test` DB, created and migrated to head.
- GitHub Actions: ruff, pytest against a Postgres service, `alembic upgrade head → downgrade -1 → upgrade`.
- mypy configured (`explicit_package_bases`).

**C3 scope:**
- An `AuthProvider` port.
- A dev token issuer (HS256, `/auth/dev-login`, available only in `development`).
- An OIDC/JWKS verifier for staging/prod (config only until a vendor is chosen).
- `ENVIRONMENT` fails closed.
- The dev fallback is removed. Header identity remains in `test` only.
- The Streamlit login screen sends a Bearer token.

**C4/C5 scope:**
- Tables: `memberships`, `project_memberships`, `role_templates`, `capabilities`, with a backfill from `users.role` and project creators.
- A `require(capability)` dependency on every route.
- Scope the unscoped getters and validate foreign IDs.
- Add `organization_id` to scenes, entities, candidates and `project_versions` (with backfill).
- `for_update` on every version bump, plus `uq_project_versions_project_number` after a duplicate pre-check.
- The unknown approval scope returns 422.
- `assets.size_bytes` becomes `BigInteger`.

**C6 scope:**
- `sync_execution` defaults to false (true stays in tests).
- The outbox gains lease, heartbeat, `next_attempt_at`, `max_attempts`, a dead-letter queue and a stale-claim sweep.
- Redelivery resumes from the checkpoint.
- Idempotent `propose_*`.
- Checkpointer `setup()` runs once.
- `Idempotency-Key` on POSTs.
- The outbox `workflow_run_id` uniqueness constraint is relaxed (expand/contract).

## 6. Stage GW — Guided Workspace foundation (UX P0)

| # | Milestone | Scope | Tests / exit criteria | Size |
|---|---|---|---|---|
| **GW1** | Journey state engine (server) | **Done, 2026-11-06.** See below | Unit tests for every rule in UX §6. Applicability changes with mode (Fully AI / Hybrid / Mixed), verified against the real JRN-07.4 mode exception. Opening an item never completes it (every status transition requires an explicit `act_on_item` call; GET is read-only) | L |
| **GW2** | Design system + React production workspace shell | **Done, 2026-11-07.** See below | UI smoke tests for every state (loading, empty, error, offline, permission-denied). Keyboard-navigable expanders. UX §16 QA list items 1–10 and 13 | L |
| **GW3** | Studio Tools mapping | **Code and tests done, 2026-11-11; E2E execution pending (DEC-033).** See below | Existing slice tests pass. Each tool reachable from its section and permission-aware | M |

**GW1 scope (implemented as):**
- `packages/domain/journey.py`: the manifest loader (reads S0's `journey_manifest.yaml`, cached), the applicability resolver (mode + `shot_method_in` exception; shot methods are a stubbed empty set until D7/D9 builds a real `shots` table), and the pure status-derivation functions (subpoint → group → section), all tested with no database (`tests/unit/test_journey_domain.py`).
- Tables (migration `5915e59b2818`): `journey_item_states` (one row per project+subpoint: status, N/A reason, evidence refs, notes, actor, timestamps), `journey_section_events` (append-only "Continue" transitions with a group-status snapshot) and `journey_staleness` (open/resolved rows; `mark_stale` is idempotent). Also added `projects.production_mode` (minimal pull-forward from D1; the applicability resolver cannot function without it — DEC-021 backfill to `fully_ai`).
- `packages/services/journey.py` (`JourneyService`): ties the domain logic to persistence and to the 7 `system`-kind completion checks (querying real G-01..G-04 data — script/research/storyboard/film-bible candidates and canon), with `AuthzService.require` gating every write on the group's `act_capability`/`approval_capability` from the manifest, and `can_act`/`can_approve` reported on every read so the (future) UI can grey out what a viewer can't do.
- Endpoints (`apps/api/routers/journey.py`): `GET /projects/{id}/journey`, `POST .../journey/items/{jrn_subpoint_id}` (`action`: draft/complete/request_review/not_applicable), `POST .../journey/sections/{jrn_section_id}/continue`.
- 2 bugs found and fixed by the API-level tests (not caught by the pure unit tests): (1) `derive_section_status` read an untouched section as `in_progress` when its only non-`not_started` group was `not_applicable` by mode; (2) a `no_pending_candidates:*` system check was vacuously true before any candidate ever existed, auto-completing a review step that had never actually been reviewed.
- 35 tests total: `test_journey_domain.py` (12), `test_journey_api.py` (9), `test_journey_authorization.py` (3), `test_journey_staleness.py` (3) plus the pre-existing `test_journey_manifest.py` (S0) and `test_journey_domain.py` additions.
- Not yet wired: a real trigger calling `mark_stale` from a D-stage domain event (there is no upstream domain event worth going stale over yet); the primitive and its API-observable behaviour are tested and ready.

**GW2 scope (React, amended):**
- **New app `apps/web`:** Vite + React + TypeScript (strict), React Router, TanStack Query, a typed client generated from OpenAPI, and design tokens from Wireframe v1.1 as CSS custom properties.
- **Online Workspace:** project cards, action queue, recent activity, create and continue.
- **Project Workspace:**
  - a left 10-section journey rail with progress and locks
  - a header showing mode, screenplay version and next action
  - numbered, accessible accordions with status chips and subpoint actions
  - a "Continue to Next Section" gate with summary
  - breadcrumbs, a Studio Tools menu, a task tray, and toasts
  - loading, empty, error, offline and permission-denied states
- **Tests:** Vitest + Testing Library for components, Playwright E2E against the real API.

**GW2 — implemented as:**
- `apps/web/src/api/`: `schema.ts` generated from a live OpenAPI dump (`scripts/dump_openapi.py` + `openapi-typescript`), a thin typed `client.ts` (one `ApiError`/`UnauthenticatedError` mapping, no runtime codegen dependency at request time), and `sessionStorage`-backed token storage (`auth.ts`).
- `src/routes/LoginPage.tsx` (dev-login), `OnlineWorkspacePage.tsx` (project grid, inline create), `ProjectWorkspacePage.tsx` (the guided workspace shell itself).
- `src/components/`: `JourneyRail.tsx` (10-section nav, lock/unlock, progress bar), `AccordionGroup.tsx` + `SubpointRow.tsx` (numbered groups/subpoints, status chips, draft/complete/request_review/not_applicable actions, system-derived items show "Completes automatically" instead of a button a user can't actually press), `StatusChip.tsx` (9 statuses, text + color, never color-alone), `Toast.tsx`/`useToast.ts`, `RequireAuth.tsx`, `GlobalHeader.tsx`.
- Loading/error/empty/offline/permission-denied states are all real, not placeholders: `navigator.onLine` + `online`/`offline` listeners for the offline banner; `ApiError.status === 403` renders a permission-denied message distinct from a generic failure.
- `apps/api/schemas.py`/`routers/journey.py`: added `JourneyGroupResponse.system_managed` (additive field) so the client can tell a system-derived `validate` subpoint apart from a manual one without re-deriving `completion_check.kind` client-side.
- **Bug found and fixed while building this** (not a frontend bug): a plain org member creating their own project could never complete the journey's mandatory first section. See DEC-032 and migration `a9fb5bf54591`.
- **Tests:** 25 Vitest/Testing-Library tests (`apps/web/tests/`) covering `StatusChip`, `JourneyRail` (lock/unlock, `aria-current`), `SubpointRow` (every action/state combination, pending-disables-all), `AccordionGroup` (open/close, not-applicable body, pending targets the right row), and a mocked-API integration test of `ProjectWorkspacePage` (load → act → continue → advance; 403 → permission-denied copy). One Playwright E2E smoke spec (`apps/web/e2e/guided-workspace.spec.ts`: sign in → create project → complete a subpoint) runs locally against a real API + Postgres (DEC-031: not yet wired into CI). 2 new backend regression tests lock in `system_managed` and the project-creator capability fix. TypeScript strict, ESLint (typescript-eslint + react-hooks + react-refresh) and the full backend suite are all clean (`npx tsc -b`, `npx eslint .`, `pytest` at 201 passed, `ruff check .`).
- Not yet built (deferred to GW3 per the Streamlit-parity plan): the Studio Tools index itself (the button exists and is reachable; it currently shows a toast rather than the tool list), a task tray for async workflow runs (the backend's outbox/worker from C6 has no UI surface yet), and project settings.
- `apps/ui` (Streamlit) is untouched and still functional; it is not deleted until GW3's parity suite passes (ADR-002).

**GW3 scope:**
- The current Streamlit views are re-implemented in React as contextual tools:
  - Assets → 02.1
  - Script Intelligence and Review → 02.2/02.3
  - Historical Research → 03.2–03.6
  - Film Bible → 05.1
  - Storyboard → 06.5
  - Audit → cross-stage
- Every workflow trigger is async, with the task tray.
- **Exit:** a Playwright parity suite passes. Then delete `apps/ui`, `tests/unit/test_ui_smoke.py` and the `streamlit` dependency.

**GW3 — implemented as:**
- `apps/web/src/components/StudioToolsMenu.tsx` + `src/lib/studioTools.ts`: a small registry of the 7 tools that actually exist today (not the full 60+ `screens` list in the manifest, most of which are D-stage features not built yet), each tagged with the journey section(s) it is reachable from; `review` and `audit` are cross-stage (always shown). Replaces GW2's toast stub.
- `src/components/StudioToolPanel.tsx`: a generic modal shell (title, Escape-to-close, focus-on-open) every tool renders into.
- `src/components/tools/`: `AssetsTool` (upload + list, JRN-02.1), `ScriptIntelligenceTool` (trigger G-01, JRN-02.2), `ReviewTool` (approve/reject candidates from any of the 4 graphs, cross-stage), `HistoricalResearchTool` (investigate/questions/sources/claims/conflicts tabs, JRN-03.2–03.6), `StoryboardTool` (board + generate tabs, JRN-06.5), `FilmBibleTool` (rules/synthesize/scenes/entities/versions tabs, JRN-05.1), `AuditTool` (JRN-10, cross-stage). Each mirrors its Streamlit predecessor's behaviour (same checkbox-default-all-selected approve flow, same tab layout) against the real API, not a reinvention.
- `src/hooks/useWorkflowRun.ts` + `useTaskTray.ts` + `components/TaskTray.tsx`: every workflow trigger is async by default (C6, `sync_execution: false`); a tracked run polls `GET /workflow-runs/{id}` every 2s until it reaches a terminal `WorkflowStatus` (`awaiting_approval`/`completed`/`rejected`/`failed`), surfacing a "Review" action once a human gate opens and the run's `error_message` on failure.
- `apps/web/src/api/client.ts`: extended with every remaining endpoint (assets incl. multipart upload, candidates/approvals, research questions/sources/claims/conflicts, storyboard panels, film-bible rules, the 4 workflow triggers), typed from the same OpenAPI-generated schema as GW1/GW2 -- no new backend endpoints were needed, since C1–C6 already expose the full surface the old Streamlit views used.
- Permission-awareness: enforced server-side as before (`AuthzService.require`); a 403 renders the same "you don't have permission" copy as the rest of the app (`src/lib/describeError.ts`, factored out of `ProjectWorkspacePage` for reuse) rather than a dedicated client-side capability-check endpoint.
- **Tests:** 14 new Vitest/Testing-Library tests -- `StudioToolsMenu` (section filtering, cross-stage tools, open callback), `TaskTray` (status badges, Review action, dismiss only when terminal, error message), `AssetsTool` (empty/list/upload), `ReviewTool` (renders proposed candidates, approves only checked ones with the exact `ApprovalDecisionRequest` shape, rejects with none) -- bringing the `apps/web` suite to 39 tests, all passing. TypeScript strict and ESLint are clean. 2 Playwright E2E specs were written (`guided-workspace.spec.ts` from GW2, plus `studio-tools-pipeline.spec.ts`: sign in → upload a screenplay → trigger Script Intelligence → wait for the task tray's worker-driven "Review" state → approve → confirm the canonical scene appears in the Film Bible tool) and a 3rd `webServer` entry (the real worker process) was added to `playwright.config.ts` for this, but **neither spec has actually been run**: this sandbox cannot resolve `cdn.playwright.dev` to download a Chromium binary (see DEC-033). Run `npm run e2e` on a networked machine before treating GW3 as verified end-to-end.
- `apps/ui` (Streamlit) is **not deleted**: per "existing functionality protection", that only happens once the Playwright parity suite is confirmed green, which this environment could not do. The streamlit dependency and `tests/unit/test_ui_smoke.py` are untouched.

## 7. Stage C (continued) — remaining hardening

| # | Milestone | Scope | Tests / exit criteria | Size |
|---|---|---|---|---|
| **C7** | Secure media | **Done, 2026-11-11** (presigned upload and ffprobe deferred -- DEC-036, DEC-035). See below | A 2 GB streamed upload keeps API memory flat. A signature mismatch is rejected. Parser golden files pass | L |
| **C8** | Generalised approvals + append-only audit | **Done, 2026-11-11** (routing-logic generalization and `level`/`required_capability` deferred to D2 -- DEC-038). See below | Existing approval tests unchanged. A direct canon write without the capability is denied | M |
| **C9** | Observability + containers | **Done, 2026-11-11, verified against a real running stack.** See below | One trace spans API → worker. `docker compose up` starts all services | M |
| **C10** | ModelGateway | **Done, 2026-11-11.** See below | Every generator goes through the gateway. The mode is visible in the UI. The eval harness runs | L |

**C7 — implemented as:**
- `packages/storage/service.py`: `StorageService.store_stream` is now a real streaming implementation -- reads in bounded chunks (default 1MB, configurable via `storage_stream_chunk_bytes`), computes the SHA-256 checksum incrementally, validates the first chunk's magic-byte signature, and enforces `max_size_bytes` mid-stream (raising `PayloadTooLargeError` without ever buffering the rest of an oversized upload). Writes to a temp file in the destination directory first, then `os.replace`s it into the content-addressed final path -- atomic, and never leaves a partial file visible at the real path. `store_bytes` is now a thin wrapper over `store_stream` (`io.BytesIO`), not a separate code path.
- `apps/api/routers/assets.py`: the upload route passes Starlette's `file.file` (the request's own spooled/disk-backed buffer) straight into the streaming store, instead of `await file.read(limit+1)` materialising the whole request body as one `bytes` object first -- the actual fix for the "2 GB upload keeps memory flat" criterion.
- `packages/storage/magic_bytes.py`: signature checks for every allowlisted type (PDF `%PDF-`, DOCX/OOXML's zip signature, "no NUL byte" for the text-like types) -- dependency-free, no `libmagic`.
- `packages/storage/s3_service.py`: `S3StorageService`, tested against `moto`'s in-process S3 mock (`tests/unit/test_s3_storage_service.py`) rather than a real MinIO container -- see DEC-034 for why (MinIO retired its free container images in Sept 2026). Reads the incoming stream into a `SpooledTemporaryFile` itself (computing the checksum and enforcing the signature/size checks before boto3 ever sees it), deliberately not handing boto3 a live, partially-validated stream to read from directly -- its multipart transfer manager runs on background threads and wraps read-time exceptions in its own `S3UploadFailedError`, which would have swallowed `PayloadTooLargeError`/`UnsupportedMediaTypeError` before `apps/api/errors.py` ever saw them.
- `packages/domain/enums.py` (`AssetScanStatus`) + migration `5e0116cc8b0b` (expand → backfill-to-`clean` → contract, same pattern as every prior required-column migration): every asset starts `quarantined`, and `packages/services/scanning.py`'s `NoOpScanner` (synchronous, dev/test default) marks it `clean` without reading its content -- a real scanner later reads the asset back as a stream from `StorageService`, the same memory-bounded way it was written, never from an in-memory blob.
- `packages/services/extraction.py` + the new `asset_derivatives` table: real text extraction for PDF (`pypdf`), DOCX (`python-docx`) and Final Draft `.fdx` (stdlib XML via `defusedxml`, which blocks XXE/entity-expansion attacks on this untrusted-upload input) -- before this, `ScriptReviewService.load_script_text` rejected every non-`text/*` asset outright, so a PDF or Word screenplay could be uploaded (both were already upload-allowed for other purposes, e.g. research sources) but never actually used for Script Intelligence. Extraction output is shaped to match what `packages/workflows/script_intelligence/parser.py` already expects (one slugline or character cue per line), so the existing parser needed no changes. A malformed document fails extraction gracefully (the asset still uploads; Script Intelligence then reports a specific "could not extract text" reason) rather than failing the upload for an unrelated reason.
- **Tests:** 255 passed total (up from 234 before this milestone). New: `tests/unit/test_s3_storage_service.py` (6), `tests/integration/test_storage_service.py` additions (4: chunked streaming checksum, size-limit cleanup, signature mismatch, store_bytes-via-store_stream parity), `tests/unit/test_extraction.py` (6: real in-memory PDF/DOCX/FDX fixtures, a malformed-file case per format, an unrecognised-mime-type case), `tests/api/test_document_format_ingestion.py` (5: PDF/DOCX/FDX actually parse into real scene/entity candidates end-to-end through the HTTP API, a corrupt PDF fails with a specific message, a byte-content/declared-type mismatch is rejected at upload). 2 pre-existing tests that happened to upload plain text mislabelled as `application/pdf` (to test an unrelated path) were updated to use `application/json` instead, since the new magic-byte check now correctly rejects that mismatch. Frontend: `AssetsTool`/`ScriptIntelligenceTool` updated to show real scan status and only offer scanned-clean assets to trigger a workflow against; 2 new/updated Vitest tests.
- Migration round-tripped (`alembic downgrade base` → `upgrade head`) clean; ruff clean on the whole repo.
- **Deferred, with reasons recorded:** MinIO-in-compose (DEC-034), ffprobe media metadata (DEC-035, no media-ingestion feature exists yet to attach it to), presigned direct-to-S3 upload (DEC-036, a materially different flow deserving its own design pass).

**C8 — implemented as:**
- `audit_events` is genuinely append-only now: migration `509b44e10054` adds a `BEFORE UPDATE OR DELETE` trigger (`prevent_audit_event_mutation`) that raises unconditionally unless the session has explicitly run `SET LOCAL tattva.allow_audit_mutation = 'true'` first. This is a trigger, not a DB-role GRANT/REVOKE, because every environment this runs in today (dev/test/CI) connects as the `postgres` superuser, which bypasses table grants entirely -- a grant-based approach would enforce nothing and be untestable here (DEC-037). The one legitimate mutation in the whole codebase, `tests/support.py::purge_organization`'s per-test teardown delete, uses the scoped override; every other audit write path (`AuditRepository.record`, called from every service) only ever inserts and is completely unaffected.
- `approval_requests` gains a generic target: `workflow_run_id` is now nullable, with `target_type`/`target_id` as the alternative a future non-workflow-run approval (e.g. D2's screenplay-lock decision) would use instead. Purely additive -- every approval created by the 4 existing graphs still has `workflow_run_id` set, and `apps/api/routers/approvals.py`'s decision routing is unchanged. The `level`/`required_capability` half of the original scope, and the routing-logic generalization itself, are deferred to D2 (DEC-038): building them now, with no real non-workflow-run approval type to validate the shape against, risks guessing wrong and needing a second migration anyway.
- "Manual canon writes go through approval or a capability-gated direct path" was already true going in (`research.py::create_question/create_source`, `film_bible.py::create_rule` all call `AuthzService.require(actor, "canon.propose", project)` before writing directly, no approval step) -- this predates C8 (landed with C5's RBAC rollout) and needed no change; verified as part of this milestone's audit rather than re-fixed.
- **Tests:** 259 passed total (up from 255). New: `tests/unit/test_audit_append_only.py` (4: a raw UPDATE is rejected, a raw DELETE is rejected, INSERT is unaffected, the override is transaction-scoped and doesn't leak to a fresh session). `ApprovalResponse`'s `workflow_run_id` became `str | None` to honestly reflect the now-nullable column, which TypeScript's strict null-checking caught immediately in `ReviewTool.tsx` (a real, if currently unreachable, display path for a future target-based approval was added there too).
- Migration round-tripped clean; ruff and the frontend's tsc/eslint clean.

**C9 — implemented as:**
- `packages/core/logging.py`: JSON structured logging everywhere (switchable to plain text via `LOG_FORMAT=text`, a local-debugging convenience). Every log line carries `request_id` (one per HTTP request, `apps/api/correlation_middleware.py`'s `CorrelationIdMiddleware` -- generates one or honours an incoming `X-Request-ID`, echoes it back in the response) and/or `run_id` (set for the duration of the worker processing one outbox task, `apps/worker/worker.py`'s `process_one_task`), via `contextvars` so no call site has to pass them explicitly.
- `packages/core/tracing.py`: OpenTelemetry tracing, `FastAPIInstrumentor`-instrumented. No backend is wired up (spans export to the console, `ConsoleSpanExporter` + `SimpleSpanProcessor` -- not `BatchSpanProcessor`, which raced its background export thread against process shutdown under pytest); set `OTEL_EXPORTER_OTLP_ENDPOINT` to point at a real collector (Tempo/Honeycomb/Jaeger) with no other code change. The API captures the current span's context (`inject_trace_context`) directly into the outbox task's existing `payload` JSON column when enqueuing (`packages/services/{script_intelligence,historical_research,storyboard,film_bible}.py`); the worker extracts it back (`continue_trace`) when claiming the task, starting its own span as part of the *same* trace.
- `apps/api/routers/health.py`: `/health` (kept, unchanged) plus `/health/live` (no dependency check -- a liveness probe an orchestrator uses to decide whether to restart the process) and `/health/ready` (checks the database -- a readiness probe that controls traffic routing, not restarts, since restarting the API wouldn't fix a database outage).
- `apps/api/Dockerfile`, `apps/worker/Dockerfile`, `apps/web/Dockerfile` (multi-stage: `node:20-alpine` build, `nginx:alpine` serve), `docker-compose.yml` (`db`, a one-shot `migrate` running `alembic upgrade head`, `api`, `worker`, `web`, with healthchecks and `depends_on: condition: service_healthy`/`service_completed_successfully` so nothing starts before its dependency is actually ready). No `apt-get`/`apk add` anywhere -- extraction (C7) is already pure-Python, and every healthcheck uses the interpreter/busybox already in the image (Python's `urllib` for api/worker, `wget` -- bundled in `nginx:alpine`'s busybox -- for web), both because this sandbox's network reached PyPI/npm/Docker Hub fine but not Debian's or Alpine's own package mirrors, and because it is simply fewer moving parts for a real deployment either way.
- **Verified against a real, running stack**, not just written: built all three images, ran `docker compose up -d --build` (all 5 containers reached their expected state: `migrate` exited 0, `api`/`web` healthy, `worker`/`db` up), then drove the real HTTP API through nginx's proxy end to end -- `/health`, `/health/live`, `/health/ready` all responded; `X-Request-ID` was generated and echoed; `dev-login` → create a project → upload a real screenplay (streaming, C7) → trigger Script Intelligence asynchronously all worked through the containerized API, Postgres and worker together. Inspecting the containers' own JSON logs directly confirmed `service.name` distinguishes `tattva-api` from `tattva-worker`, and comparing the trace IDs in each process's span output confirmed the SAME trace_id appeared in both -- the literal exit criterion, observed in the running system.
- **A real bug found and fixed by that live verification, not by the unit tests**: the API correctly injected `traceparent` into the outbox task's `payload`, but the worker read it back from a key (`"trace_context"`) that was never actually there -- `inject()` writes directly into the given dict, not under a sub-key -- so it silently fell back to an unrelated root span every single time. The original unit test (`tests/unit/test_tracing.py`) exercised the `inject_trace_context`/`continue_trace` primitives correctly in isolation and could not have caught this: the bug was in the integration glue in `apps/worker/worker.py`, not in those primitives. Fixed, and locked in with a new test that exercises the real enqueue → claim path end to end (`tests/workflows/test_worker.py::test_the_api_trigger_and_the_worker_that_processes_it_share_one_trace`) -- confirmed it fails against the old code and passes against the fix, then re-verified the fix against the live containers a second time.
- Also found and fixed while building the Dockerfiles: `TracerProvider(Resource.create(...))` passed the resource as the first positional argument, which `TracerProvider.__init__` actually binds to `sampler` -- would have raised `AttributeError: 'Resource' object has no attribute 'should_sample'` on the very first traced request in any real deployment (not caught by the unit tests, which reset tracing manually and never called `configure_tracing` itself); caught by running the real test suite with tracing wired into `create_app` for the first time.
- **Tests:** 270 passed total (up from 259 before this milestone). New: `tests/unit/test_tracing.py` (3: trace propagation primitives), `tests/api/test_health_and_observability.py` (7: all three health routes, liveness never touches the DB, request-ID generation/preservation/uniqueness, the JSON formatter produces real parseable single-line JSON), `tests/workflows/test_worker.py` (1: the real end-to-end trace-sharing regression test above).
- Migration/schema: none -- C9 added no tables or columns; the trace context reuses `outbox_tasks.payload`, which already existed.

**C10 — implemented as:**
- `packages/ai/gateway.py`: a formal `ModelGateway` ABC (`parse_screenplay`, `investigate_history`, `align_storyboard`, `synthesize_film_bible`) and `DeterministicModelGateway`, the only implementation today -- a thin wrapper around the 4 generators that already existed (`script_intelligence/parser.py`, `historical_research/investigator.py`, `storyboard_intelligence/aligner.py`, `film_bible_synthesis/synthesizer.py`). Their own logic is untouched; they're genuinely real (parameterised on real scene/claim input), not placeholders -- only now called through one interface instead of 4 graphs each instantiating and calling its own generator class directly. `get_model_gateway(settings)` is the one factory every caller uses, switched by `MODEL_GATEWAY_PROVIDER` (`deterministic` today; `llm` reserved -- same ABC, same Pydantic models, a future real adapter is a config change, not a graph rewrite).
- `packages/ai/schemas.py`: one Pydantic result model per capability (`ScreenplayParseResult`, `HistoricalResearchResult`, `StoryboardAlignResult`, `FilmBibleSynthesisResult`), field-for-field matched to what the 4 review services' `propose()`/`propose_candidates()` methods already required (verified by reading each, not assumed) -- a malformed shape now fails as one clear `ValidationFailure` (422) at the gateway boundary instead of a `KeyError`/`TypeError` deep inside a later DB-write transaction.
- `generator_mode` persisted on `workflow_runs` and all 6 `*_candidates` tables (migration `b8a9dc799b50`, expand → backfill-to-`deterministic` → contract -- every run/candidate that existed before this migration really was produced by one of the 4 deterministic generators, so the backfill value is what actually happened, not a guess). Each of the 4 services' `start()` sets it from `get_model_gateway(get_settings()).mode` when creating the run; each review service's `propose()`/`propose_candidates()` reads it back off that same run row (`self.runs.get(...)`, already fetched for version-check purposes) and stamps it onto every candidate it writes -- one source of truth, no value threaded through graph state.
- The 4 graph node functions (`parse_script_node`, `investigate_node`, `generate_panels_node`, `synthesize_visual_rules`) now call the gateway instead of instantiating a generator class directly, converting the returned Pydantic model back to dicts (`.model_dump()`) before returning into graph state -- zero change to any downstream consumer's expected shape.
- `apps/api/schemas.py`: `generator_mode: str` added to `WorkflowRunResponse` and all 6 candidate response models; `apps/web/src/components/tools/ReviewTool.tsx` shows it as a small badge on each pending-approval card (satisfying "the mode is visible in the UI") -- regenerated `openapi.json`/`src/api/schema.ts`.
- **Circular import found and fixed**: `packages/workflows/__init__.py` eagerly re-exports from `script_intelligence`, which (after this change) imports `packages.ai.gateway` at module load; `gateway.py` importing the 4 generator classes at its own module top level created an import cycle through `packages/workflows/film_bible_synthesis/__init__.py`. Fixed by deferring those 4 imports to inside `DeterministicModelGateway.__init__` (by construction time -- a node function actually running -- every module involved is already loaded).
- **Eval harness**: `tests/unit/test_model_gateway_golden.py` -- one small, real, runnable fixture per capability (the same sample screenplay/scenes/claims used elsewhere in the test suite), asserting schema-valid output grounded in the given input and determinism (same input twice -> identical `model_dump()`). A future LLM-backed gateway is held to the same fixtures and grounding assertions, loosened from exact-match to semantic, but not to the determinism assertions.
- **Tests:** 279 passed total (up from 270 before this milestone; +9 golden-harness tests). Migration round-tripped (`alembic upgrade head` → `downgrade -1` → `upgrade head`) clean; ruff clean; frontend `tsc -b`/`eslint .`/`vitest run` all clean.

## 8. Stage D — FD-V1 product completion, built in journey order

Each section lands as a vertical slice (UI → API → authZ → service → DB → approval → audit/version → tests) inside the Guided Workspace.

| # | Journey section | Roadmap pkg | Highlights | Size |
|---|---|---|---|---|
| D1 | **01 Project Workspace & Setup** | D1 | **Done, 2026-11-12** (scope follows the roadmap's TFD-PRJ-001…004/007 + TFD-FMT-001…004, narrower than this row's summary -- DEC-041). See below | M |
| D2 | **02 Screenplay & Governance** | D2 + D3 | **Done, 2026-11-13** (TFD-SCR-001…010 from 2026-11-12, plus roadmap pkg D3's Story Intelligence v2 slice -- TFD-STY-001…003/007 -- added 2026-11-13; TFD-SCR-011/TFD-APR-007 structural-only/deferred -- DEC-046; TFD-STY-004/005/006 Story Brain deferred to the row below -- DEC-052). See below | XL |
| D3 | **03 Research & Story Intelligence** | D4 + D8 | Story Brain (TFD-STY-004/005/006, deferred from above until D4/`character_states` exists -- DEC-052); research through approval; locators; `timeline_events` with uncertain dates; fact / evidence / interpretation / dramatization labels; Context Resolver | L |
| D4 | **04 Character & Digital Human** (V1 foundation) | D5 | `characters` (legacy link to `entities`); identity, facial, physical and performance profiles with a provenance envelope; measurements (estimated vs verified); `performers`, `performer_consents` with enforcement points; avatar approach; voice profile record | XL |
| D5 | **05 Visual World** | D6 + D7 | Costumes and states, props/weapons and states, locations, environments and states; Visual Language Profile (the generalised Film Bible) | L |
| D6 | **06 Cinematography & Storyboard** | D7 + D9 | Cinematography Bible, camera/lens/lighting profiles, `camera_spec` (physical / virtual, actual / creative target / recommended); AI recommendation with override; storyboard image/PDF ingestion and mapping | XL |
| D7 | **07 Production Planning** | D9 + D10 | Sequences; shots with `production_method`; capture plan record (V1 manual form; WF-12 automation in V2); continuity rules with the 9 dimensions and 9 states; production readiness check; AI Director review | XL |
| D8 | **08 Tool Handoff (manual)** | D11 | Provider-neutral Shot Spec; prompt compiler; immutable `production_packages`; copy / JSON / Markdown / ZIP export with manifest and checksum; manual run record; output import mapped to shot; manual-only registry entries | L |
| D9 | **09/10 V1 foundations** | D11 + D12 | Manual output review and approval; production library with lineage; JSON/CSV handoff manifest | M |
| D10 | FD-V1 stabilisation | D12 | Pilot on the two DEC-028 productions; golden-set evaluation reports; accessibility pass (WCAG 2.2 AA); UX §16 QA list | L |

**D1 — implemented as:**
- `packages/domain/format_templates.py`: a code-defined catalogue of all 13 production formats from PRD §8 (`FORMAT_TEMPLATES`/`FORMAT_TEMPLATES_BY_KEY`), each with a `structure_type` (`linear`/`episodic`), required/optional Guided Workspace workflow steps (JRN-02..JRN-10 -- Reel/Social marks JRN-07 optional per AT-FMT-001.2; Trailer/Teaser mark most mid-pipeline steps optional since they reference a parent project's shots; Documentary marks JRN-02 optional for its footage-first/optional-lock path), and a provisional `default_output_profile`. Served read-only via `GET /project-templates` (`apps/api/routers/project_templates.py`). Per-format numeric defaults are explicitly provisional pending production validation (DEC-028).
- `packages/domain/enums.py`: `ProductionMode` (validated at the API boundary -- an out-of-range value 422s, AT-PRJ-003.1), `QualityProfile`, `ProjectScale` (both provisional placeholder value sets -- DEC-042, same gate as DEC-028).
- Migration `63e256a9e65a` (two new tables, purely additive nullable columns, no backfill needed) + `29c39597195d` (seeds the new `project.manage_members` capability and grants it to the `project_owner`/`management` role templates for every existing org, following the same pattern as the RBAC seed migration and `a9fb5bf54591`):
  - `projects` gains `format_template_key`/`quality_profile`/`scale` (all null = "decide later", AT-PRJ-001.1).
  - `scenes` gains a nullable `production_mode` override (null = inherit the project's mode, TFD-PRJ-004) and a nullable `episode_id` (TFD-FMT-003's structural foundation -- DEC-043 scopes the rest of episodic structure, the D2-dependent locked-screenplay-per-episode piece, to D2).
  - New `output_profiles` table (TFD-FMT-002: resolution, aspect ratio, fps, duration target, audio, subtitles, delivery format, platform notes, one `is_default`) and `episodes` table (TFD-FMT-003, unique per `(project_id, episode_number)`).
- `packages/services/projects.py` (`ProjectService`), substantially extended:
  - `list()`/`get()` are now genuinely membership-scoped (TFD-PRJ-002): an org owner sees every project; any other member sees only their own `project_memberships`, and a project outside that set 404s rather than 403ing (AT-PRJ-002.1 -- DEC-045; the prior 403 leaked the project's existence to any org member).
  - `create()` accepts the new "decide later" fields and validates `format_template_key` against the catalogue; the legacy `{title, logline, genre}` body (no mode given) now defaults to `mixed`, not the previously-undocumented `fully_ai` DB-column default (AT-PRJ-001.3 -- DEC-044).
  - `update()`/`archive()`/`unarchive()`: PATCH semantics (only present fields change), audited with before/after values; archive is a `status` transition (soft, reversible, AT-PRJ-002.2) -- `projects.status` already existed but was never previously consulted by any query.
  - Output profiles and episodes: full CRUD/create+list, `project.admin`-gated for writes.
  - Members & roles (S-TEAM-02): `list_members`/`add_member`/`update_member_role`/`remove_member`, gated on the new `project.manage_members` capability; `add_member` resolves an email to an existing active org member (there is no "invite a stranger" flow yet -- that's org-level S-TEAM-01); removing or demoting the project's only `screenplay.approve_lock` holder is blocked (AT-TEAM-02.1, enforced unconditionally rather than only "once a screenplay is locked", since no screenplay can be locked until D2 -- strictly more conservative, already satisfies the rule once D2 lands).
  - `summary()` (TFD-PRJ-007, Project Overview): project version, pending-approvals count, running tasks, recent changes, a scene-level mode-distribution proxy (labelled honestly -- the literal shot-level distribution doesn't exist until D9), and a `next_action` derived from the existing Guided Workspace journey engine (`packages/services/journey.py`, reused rather than reimplemented). Screenplay version/lock state and continuity findings are honestly reported as "not yet available" (`none_locked`, count `0`) rather than fabricated from an unrelated table -- `screenplay_versions` (D2) and `continuity_findings` (D10) don't exist yet (AT-PRJ-007 #1).
- `apps/api/schemas.py`/`apps/api/routers/projects.py`: `ProjectUpdateRequest`, `FormatTemplateResponse`, `OutputProfile*`, `Episode*`, `ProjectMember*`, `RoleTemplateResponse`, `ProjectSummaryResponse`, and the corresponding routes (`PATCH`/`DELETE` on `/projects`, the first in this codebase -- CORS `allow_methods` updated to include them).
- Frontend: `OnlineWorkspacePage.tsx`'s project-creation form gained a production-mode and format-template selector (S-GLB-02) and an "include archived" toggle; three new Studio-Tools-style panels -- `ProjectOverviewTool.tsx` (S-PRJ-01, wired into the Studio Tools menu as a new cross-stage entry), `ProjectSettingsTool.tsx` (S-PRJ-02: metadata/mode/template/quality/scale, output profiles, episodes, archive/unarchive) and `ProjectMembersTool.tsx` (S-TEAM-02) -- replacing `ProjectWorkspacePage.tsx`'s "Project Settings aren't built yet" placeholder button.
- **Tests:** 297 passed total (up from 279 before this milestone; +18 in `tests/api/test_project_workspace_settings.py` covering every AT- criterion in scope). 2 pre-existing tests were updated for deliberate, spec-driven behavior changes (DEC-044, DEC-045). Frontend: 50 Vitest tests passed (up from 43; +7 across 3 new component test files). Migration round-tripped (`alembic downgrade` through both new revisions and back) clean; ruff and the frontend's `tsc -b`/`eslint .` clean.

**D2 — implemented as:**
- 4 new tables -- `screenplay_versions` (the state machine: `draft -> in_review -> approved_locked -> superseded`, or `in_review -> rejected`/`-> draft` on "changes requested"; `is_production_canonical`, `derived_from_version_id`, `content_text`/`content_hash`), `screenplay_suggestions` (the 7 kinds from PRD §3 Workflow 2), `screenplay_changes` (one row per revision-submission: a computed diff + the required justification -- DEC-047), `impact_analyses` -- plus nullable `scenes.screenplay_version_id`/`review_status`, `entities.review_status`, and `workflow_runs.screenplay_version_id` (which specific version WF-01 read, following C10's "metadata lives on the run" pattern, DEC-040's sibling).
- `packages/services/screenplay.py` (`ScreenplayGovernanceService`) -- not a LangGraph workflow (there's no AI-authored content to generate-then-approve here, just a state machine plus human review): import from an asset (TFD-SCR-001), create/edit a draft revision, a line-level + scene-level diff (`difflib`, re-parsing both texts with the existing `ScreenplayParser`) computable between any two versions, submit-for-review (422 without a justification, AT-SCR-006.2), and `decide_revision` (approve -> locks + supersedes the old canonical + computes an impact analysis; reject -> terminal; changes-requested -> back to `draft`), reusing C8's generalized `ApprovalRequestModel` target for the management decision instead of a new table (DEC-047). `confirm_legacy_lock` is the explicit project-owner action the PRD's own migration note requires for promoting a backfilled v1 (no automatic promotion from the migration itself).
- Impact analysis (TFD-SCR-010): scoped honestly to what existed on 2026-11-12 -- scenes and the characters (entities) that appeared only in a changed/removed scene; sequences/shots/packages don't exist until D9/D11 (`dialogue_segments` landed the next day, see the Story Intelligence v2 slice below -- impact analysis itself was not revisited to add dialogue-level scoping, since TFD-SCR-010's own text only names scenes and characters). Flags existing canonical rows `review_status=review_required`; nothing else propagates automatically, matching PRD §3.1 invariant 4 exactly. A read-only `impact-preview` endpoint lets management see the same computation *before* deciding (AT-SCR-010.2).
- A 5th ModelGateway capability (C10 pattern): `packages/workflows/screenplay_suggestions/suggester.py` (`ScreenplaySuggester`, genuinely parameterized on the screenplay's own parsed scene structure -- short/long scenes, character counts, repeated location/time-of-day, the director's own scope notes) + `packages/ai/schemas.py`/`gateway.py` additions (`suggest_screenplay_revisions`).
- WF-01 retargeted (TFD-SCR-004): `ScriptIntelligenceService.start()` now takes `screenplay_version_id`, not `script_asset_id`; `parse_script_node` reads `screenplay_versions.content_text` directly. This is a real, deliberate breaking API change (`WorkflowTriggerRequest.screenplay_version_id` replaces `.script_asset_id`) -- every call site (6 backend test files, `ScriptIntelligenceTool.tsx`) was updated, not shimmed, per the "switch" step of the PRD's own expand -> backfill -> switch -> contract migration note.
- Migration `74e3d4a1909a` (schema) + `910fdd9ce4ec` (seeds the new `screenplay.propose_revision` capability, granted to `project_owner`/`director`) + `45c4034d8e34` (backfills one `draft` v1 per project that already has committed scenes, with real extracted content -- never auto-promoted to locked, per the PRD's "only if a project owner confirms it") + `5f62214d24dd` (`workflow_runs.screenplay_version_id`).
- **Two real correctness bugs found and fixed by actually writing the acceptance-criteria tests, not by inspection** (DEC-050, DEC-051): the "exactly one canonical version" partial unique index silently didn't enforce anything for any non-episodic project (Postgres's default `NULLS DISTINCT` never treats two `NULL` episode_ids as duplicates) -- fixed with PG15+'s `NULLS NOT DISTINCT`; and approving a revision could fail against *itself* (no concurrency needed) because the old-canonical-supersede and new-canonical-promote updates could flush in either order within one transaction, transiently leaving two canonical rows before the unique index (checked per-statement, not deferred) saw either as superseded -- fixed by flushing the supersede first. Both were caught specifically because the concurrency acceptance criterion (AT-SCR-002.2) was tested for real, including discovering that a naive `threading.Thread`-based HTTP race test was itself unreliable here and replacing it with a deterministic test of the DB constraint directly.
- Frontend: `ScriptIntelligenceTool.tsx` now imports a screenplay version from an asset before triggering WF-01 (instead of triggering straight off the asset); a new `ScreenplayGovernanceTool.tsx` (S-SCR-01…04: version history with inline create-revision/edit/diff/submit/decide actions, the Suggestions Workspace, and impact analyses) added to the Studio Tools menu.
- **Tests:** 311 backend tests passed (up from 297; +14 in `tests/api/test_screenplay_governance.py` covering the acceptance criteria above, plus fixes to 6 existing test files for the WF-01 API change). Frontend: 53 Vitest tests (up from 50; +3 for `ScreenplayGovernanceTool`, `ScriptIntelligenceTool`'s rewritten accordingly). Migration round-tripped (all 4 new revisions, down and back) clean; ruff, `tsc -b` and `eslint .` clean.

**D2 (Story Intelligence v2 slice, roadmap pkg D3's foundational pieces, TFD-STY-001…003/007) — implemented as:**
- `ScreenplayParser.parse()` now returns a 3-tuple `(scenes, entities, dialogue_segments)`: verbatim dialogue segments (speaker, line, parenthetical, order-in-scene, source locator) plus Fountain's spec-defined `@`-forced-cue convention for non-uppercase character names (`https://fountain.io`), and accumulated alias variants per entity -- a real parser capability, not a placeholder (DEC-053).
- 4 new tables: `characters`/`locations` (canonical identity per project, `(project_id, canonical_name)` unique, growing `aliases`), `dialogue_segment_candidates`/`dialogue_segments` (the latter immutable by construction -- no service method ever updates a row). `entities`/`entity_candidates` gain `aliases`; `entities` gains nullable `resolved_character_id`/`resolved_location_id` -- the same "legacy entity link" pattern as D1's `episode_id`/D2's `screenplay_version_id` (additive nullable FK on the many side). Migration `f737ff6ed5ca` (named FK constraints; expand -> contract for the new NOT NULL `aliases` columns via `server_default`), round-tripped clean.
- `ScriptReviewService.propose()` now also proposes dialogue candidates; `promote_approved()` resolves each promoted character/location entity into a `characters`/`locations` row (reusing an existing row by exact canonical-name match across workflow runs and growing its `aliases`, rather than duplicating one per run -- DEC-054) and promotes dialogue segments gated on their *own scene's* approval, not an independent review step, matched by `scene_number` within the same run (DEC-053).
- 3 new read-only endpoints (`GET /projects/{id}/dialogue-segments`/`/characters`/`/locations`) + `ProjectService` methods.
- Golden screenplay set (TFD-STY-007, DEC-055): `tests/golden/test_golden_screenplay_set.py` -- a small, hand-crafted 3-scene/3-character fixture (including a forced `@`-cue and a parenthetical), scored for scene F1 / character F1 / dialogue exact-match against a recorded `1.0` baseline, exercised through all 4 ingested formats (Fountain, DOCX, PDF, FDX), run as ordinary pytest (already in CI, not a separate job).
- TFD-STY-004 (Story Brain), 005 (narrative timeline) and 006 (character relationships) deliberately deferred, not stubbed -- zero acceptance criteria anywhere, P1 priority, and TFD-STY-005 genuinely depends on `character_states` which doesn't exist until roadmap pkg D4/D5 (DEC-052); tracked as the D3 stage row above.
- Frontend: S-SCR-02's AC2 ("dialogue shown equals the source text byte-for-byte") and AC3 ("structured scenes and dialogue, not raw JSON") are satisfied by 3 new tabs on `FilmBibleTool.tsx` -- Dialogue (scene-grouped, verbatim `line_text`/`parenthetical`), Characters, Locations -- following that tool's existing pattern for canonical cross-stage data (it already renders Scenes/Entities this way); `ScriptIntelligenceTool.tsx` itself stays the trigger-and-import form it already was, consistent with S-SCR-02's own screen spec splitting "run analysis" from "read the breakdown" the same way the existing Scenes/Entities tabs already do.
- **Tests:** 321 backend tests passed (up from 311; +6 in `tests/api/test_story_intelligence_v2.py` covering dialogue promotion/gating, character/location resolution and reuse across runs, and the forced-cue path end to end, +4 in `tests/golden/test_golden_screenplay_set.py`, plus fixes to `tests/unit/test_extraction.py` and `tests/support.py::purge_organization`'s teardown ordering for the 4 new tables). Migration round-tripped clean; ruff clean. Frontend: 56 Vitest tests passed (up from 53; +3 in a new `FilmBibleTool.test.tsx`); `tsc -b` and `eslint .` clean; `openapi.json`/`src/api/schema.ts` regenerated.

**F1 — FD-V1 readiness gate:** `RELEASE_READINESS_CHECKLIST.md` FD-V1 column, all with evidence.

## 9. Stage E — FD-V2, then F2

Follows `PRODUCT_ROADMAP.md`:
- E0: production-frontend decision and interaction proof (ADR-002).
- E1/E2: registry, jobs, attempts, cost and budgets.
- E3: reference and keyframe generation.
- E4: output inspection and library.
- E5: video adapters.
- E6: hybrid capture and footage analysis (WF-12/WF-13).
- E7: voice, dubbing, lip-sync.
- E8: digital humans and performance transformation.
- E9: post handoff.

**F2 (production readiness):** security assessment, load/soak, DR drill, runbooks.

Each connected provider stays behind its terms-review gate (gate 7). Manual parity is always kept.

## 10. External inputs needed from you, and when they block

| Input | Needed by | Without it |
|---|---|---|
| OIDC vendor choice + tenant | Staging (after C3) | Local dev uses the built-in dev token issuer; staging is blocked |
| LLM provider API key + eval budget | After C10, for real AI quality | Deterministic adapter only (labelled); no AI quality claims |
| Legal consent template + retention schedule | Before any real performer data (D4) | The consent model is built and the gate blocks real likeness/voice data |
| Cloud bucket + managed Postgres | Staging | MinIO and local Postgres |
| First provider terms review + account | E1 (FD-V2) | Manual handoff only |

## 11. What starts immediately on approval

1. **S0:** commit the docs, write IA v1.1 and the Journey manifest.
2. **C1:** branch `feat/c1-g04-fix-forward` and fix G-04 until the full suite is green. You get a report with the real pytest output.
3. **C2:** test DB isolation and CI.
4. Continue down the sequence (C3 → C4/C5 → C6 → GW …), with a status report after each milestone.

I pause and ask whenever a step needs a decision not covered by `11_APPROVAL_GATE_DECISIONS.md`, or anything destructive or outward-facing: pushing, opening PRs, merging to `main`.
