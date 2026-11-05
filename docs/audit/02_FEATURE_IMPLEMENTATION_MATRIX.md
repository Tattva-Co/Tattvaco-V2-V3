# 02 — Feature Implementation Matrix

**Doc ID:** TFD-AUDIT-002 · **Audit date:** 2026-11-05 · **Baseline:** `main@b3621cb` + uncommitted G-04 WIP
**Test evidence:** full suite run on 2026-11-05: 47 passed, 5 failed, 1 error (see `01_CODEBASE_CURRENT_STATE.md` §5).

**Status legend** (from Master Prompt §16):
- `VERIFIED`: IMPLEMENTED_AND_VERIFIED
- `IMPL_NV`: IMPLEMENTED_NOT_VERIFIED
- `PARTIAL`: PARTIALLY_IMPLEMENTED
- `SCAFFOLD`: SCAFFOLDED
- `MOCKED`
- `PLACEHOLDER`
- `BROKEN`
- `NOT_IMPL`: NOT_IMPLEMENTED
- `DEFERRED`: DEFERRED_BY_SCOPE

"Verified" means **verified by an automated test executed during this audit against local PostgreSQL**, with the deterministic generators. It does **not** mean verified with real AI, real auth, under load, or in a deployed environment. None of those exist yet.

---

## 1. V1 — Film Intelligence & Pre-production (30 items)

| # | Feature | Status | Evidence (file · symbol · route) | DB entity | Test (result) | Remaining gap |
|---|---|---|---|---|---|---|
| V1-01 | Project management | PARTIAL | `apps/api/routers/projects.py` POST/GET `/projects`, GET `/projects/{id}`; `services/projects.py ProjectService` | `projects`, `project_versions` | `test_script_intelligence_slice.py`, `test_tenant_isolation_api.py` (pass) | No production format, genre taxonomy, production mode, delivery profile, templates, archive, update or delete |
| V1-02 | Team access & role model | NOT_IMPL | `services/identity.py IdentityService.resolve`: `X-Actor-ID` header only; `users.role` is never checked | `users` | none | Real authentication, memberships, project roles, capability matrix, management authority |
| V1-03 | Universal asset ingestion | PARTIAL | `routers/assets.py` upload; `storage/service.py LocalFileSystemStorageService` (SHA-256, immutable, path guard) | `assets` | `test_assets_api.py`, `test_storage_service.py` (pass) | Text-only allowlist; whole file held in memory; client-trusted MIME; PDF/DOCX decoded as UTF-8; no media, derivatives, scanning or processing states |
| V1-04 | Script intelligence | VERIFIED (deterministic) | `workflows/script_intelligence/{graph,parser}.py`; `services/script_review.py` | `scene_candidates`, `entity_candidates`, `scenes`, `entities` | `test_script_intelligence_slice.py`, `test_graph_recovery.py` (pass) | Regex parser only; no Fountain/FDX/PDF adapters, AI extraction, golden set, dialogue segments or locators |
| V1-05 | Locked screenplay governance | NOT_IMPL | A script is an `AssetModel`; no lock or version entity | — | none | `screenplay_versions`, lock state, management approval, change comparison, impact analysis |
| V1-06 | AI suggestions workspace | NOT_IMPL | — | — | none | Separate suggestion store and workflow |
| V1-07 | Historical research | VERIFIED (mocked generator) | `workflows/historical_research/*`; `investigator.py` hardcoded per keyword; `routers/research.py` | `research_questions/sources/claims/conflicts` + candidates | `test_historical_research_api.py` (pass) | Investigator is a mock; no real retrieval/LLM; source locators are thin; `get_question/get_source` are unscoped; `create_source(asset_id)` is not tenant-validated |
| V1-08 | Historical timeline | NOT_IMPL | — | — | none | `timeline_events` (historical vs story timeline) |
| V1-09 | Film Bible | BROKEN | WIP `workflows/film_bible_synthesis/*`, `routers/film_bible.py`, `services/film_bible*.py` | `film_bible_rules`, `film_bible_rule_candidates` (migration `00b7cd57e036`) | `test_film_bible_api.py`: 4 fail, 1 error; `test_worker.py::…film_bible…` fails | Defects G04-A…F (see §3) |
| V1-10 | Character Bible | PARTIAL | `EntityModel` with `category="character"`; `scenes.characters_present` JSON | `entities` | via G-01 tests | No character profile, identity, versions, relationships or states |
| V1-11 | Physical Identity Profile | NOT_IMPL | — | — | none | Measurements with provenance, confidence and verification |
| V1-12 | Costume Bible | NOT_IMPL | Mentioned only as text in `investigator.py` | — | none | `costumes`, `costume_states` |
| V1-13 | Props & weapons register | NOT_IMPL | — | — | none | `props`, `prop_states` |
| V1-14 | Environment & location Bible | PARTIAL | `scenes.location_name`; entity category `location`; `VisualRuleCategory.ARCHITECTURAL_ENVIRONMENT` | `scenes`, `entities` | via G-01 | No location or environment profiles or states |
| V1-15 | Storyboard intelligence | VERIFIED (deterministic) | `workflows/storyboard_intelligence/*` (`aligner.py`); `routers/storyboard.py` | `storyboard_panels` + candidates | `test_storyboard_api.py` (pass) | Generates from a text brief; PRD expects image/PDF panel ingestion and panel↔scene mapping |
| V1-16 | Cinematography Bible | NOT_IMPL | `VisualRuleCategory.CAMERA_LANGUAGE` only; lens notes hardcoded in `aligner.py` | — | none | Camera package, lens and lighting libraries, virtual camera profile |
| V1-17 | Camera/lens planning | NOT_IMPL | — | — | none | Extensible physical/virtual camera spec |
| V1-18 | Sequence planning | NOT_IMPL | — | — | none | `sequences` |
| V1-19 | Shot planning | PARTIAL | `StoryboardPanelModel.shot_type`, `ShotType` enum | `storyboard_panels` | via G-03 | No `shots` entity, shot spec or production method |
| V1-20 | Continuity management | NOT_IMPL | — | — | none | Rules, checks, findings, decisions, status model |
| V1-21 | Context Resolver | NOT_IMPL | — | — | none | Versioned context packages |
| V1-22 | AI Director review | NOT_IMPL | — | — | none | G-08 |
| V1-23 | Provider-neutral Shot Specification | NOT_IMPL | — | — | none | Schema plus versioning |
| V1-24 | Prompt compiler | NOT_IMPL | — | — | none | G-09 |
| V1-25 | Production package generation | NOT_IMPL | — | — | none | Manifest, checksum, export formats |
| V1-26 | Manual export & copy | NOT_IMPL | `higgsfield_integration_mode="manual_export"` config only | — | none | Entire workflow |
| V1-27 | Manual asset import | NOT_IMPL | Generic upload only; no result-to-shot mapping | — | none | Import job, mapping, lineage |
| V1-28 | Review & approval | VERIFIED (single-tier, no RBAC) | `routers/approvals.py` dispatches by `scope`; per-workflow `decide()` locks the approval row (`get_scoped(for_update=True)`) before resume | `approval_requests` | G-01/02/03 slice tests (pass) | No role policy; unknown scope falls through to the script service; no cost or management approval levels |
| V1-29 | Versions & audit | PARTIAL | `project_versions`, `projects.current_version`, `assert_expected_version`; `AuditRepository.record`, 17 `AuditAction`s | `project_versions`, `audit_events` | slice tests (pass) | Version-bump race in research/storyboard/film-bible review services (no `for_update`); no unique `(project_id, version_number)`; audit is not append-only-enforced; branches exist in name only |
| V1-30 | Core operational observability | NOT_IMPL | stdlib `logging` only; `/health` = `SELECT 1` | — | none | Request IDs, metrics, tracing, readiness, dashboards |

**Summary:**

| Status | Count |
|---|---|
| VERIFIED (deterministic/mocked, local) | 4 |
| PARTIAL | 7 |
| BROKEN | 1 |
| NOT_IMPL | 18 |

## 2. V2 — AI Production & External Generation (25 items)

No V2 capability has any implementation. Each item below is `NOT_IMPL` unless noted.

| # | Feature | Status | Evidence / note |
|---|---|---|---|
| V2-01 | Connected image generation (verified) | NOT_IMPL | No provider adapters |
| V2-02 | Manual image generation workflow | NOT_IMPL | Depends on V1-25/26/27 |
| V2-03 | Character reference generation | NOT_IMPL | — |
| V2-04 | Environment reference production | NOT_IMPL | — |
| V2-05 | Costume & prop reference production | NOT_IMPL | — |
| V2-06 | Keyframe workflows | NOT_IMPL | — |
| V2-07 | Performance-preserving transformation | NOT_IMPL | — |
| V2-08 | Digital human workflows | NOT_IMPL | — |
| V2-09 | AI anchor workflows | NOT_IMPL | — |
| V2-10 | Motion capture integration/handoff | NOT_IMPL | — |
| V2-11 | Body measurement integration/handoff | NOT_IMPL | — |
| V2-12 | Chroma & live-action production workflows | NOT_IMPL | — |
| V2-13 | Video generation via verified adapters | NOT_IMPL | Higgsfield exists only as config fields in `core/config.py` |
| V2-14 | Voice workflows | NOT_IMPL | — |
| V2-15 | Multilingual dubbing | NOT_IMPL | — |
| V2-16 | Lip-sync integration | NOT_IMPL | — |
| V2-17 | Generation job tracking | SCAFFOLD | `workflow_runs` + `outbox_tasks` provide a job concept for internal graphs only; no external job, attempt or unknown-outcome model |
| V2-18 | Generation attempt tracking | NOT_IMPL | — |
| V2-19 | Provider capability registry | NOT_IMPL | — |
| V2-20 | Cost & credit tracking | NOT_IMPL | — |
| V2-21 | Output import & inspection | NOT_IMPL | — |
| V2-22 | Continuity comparison | NOT_IMPL | — |
| V2-23 | Revision & regeneration requests | NOT_IMPL | — |
| V2-24 | Shot-level production library | NOT_IMPL | — |
| V2-25 | Production handoff package | NOT_IMPL | — |

## 3. New Master-Prompt capability families (not in PRD v0.9)

| Family | Status | Note |
|---|---|---|
| Production mode at project/sequence/scene/character/shot level (Fully AI / Hybrid / Mixed) | NOT_IMPL | No concept anywhere in code or docs |
| Digital double / fictional avatar / reusable digital human | NOT_IMPL | Absent from PRD, Addendum and IA |
| Performer consent & likeness/voice authorization | NOT_IMPL | PRD §15.5 mentions consent generically; no model or gate |
| On-set capture planning & capture manifest | NOT_IMPL | — |
| Independent footage ingestion & analysis | NOT_IMPL | — |
| Voice/dialogue (original + AI) & localisation | NOT_IMPL | — |
| Production format templates & output profiles | NOT_IMPL | `projects.genre` only |
| Post-production handoff (OTIO/EDL/XML/CSV/JSON) | NOT_IMPL | V2 handoff package; NLE is V3 |
| V3 items (NLE, VFX, grading, mastering, final render, distribution) | DEFERRED | Must not be started |

## 4. G-04 Film Bible: defect list (WIP, BROKEN)

| ID | Defect | Evidence | Effect |
|---|---|---|---|
| G04-A | `FilmBibleState` does not declare `approved_rule_ids` / `decision_notes` | `workflows/film_bible_synthesis/state.py`; LangGraph drops undeclared keys | Partial approval commits **all** rules; decision notes are lost |
| G04-B | Calls the non-existent `ResearchRepository.list_claims_for_project` (the real method is `list_claims`) | `film_bible_synthesis/graph.py:51`, `services/film_bible_review.py:162` | `AttributeError`; every synthesis run fails (confirmed in the test run) |
| G04-C | `tests/support.py::purge_organization` was not extended to the film-bible tables | Teardown `ForeignKeyViolation film_bible_rules_project_id_fkey` | Test error; orphan rows left in the dev DB |
| G04-D | `POST /projects/{id}/film-bible/rules` writes canonical rules directly | `FilmBibleService.create_rule` | Bypasses approval, versioning and enum validation; `historical_claim_id` is not tenant-checked |
| G04-E | Synthesizer output is hardcoded (Mauryan/Kalinga rules), ignores scenes, and links claims by statement text | `synthesizer.py`, `conflict_detector.py` | PLACEHOLDER-grade intelligence |
| G04-F | Re-runs accumulate duplicate canonical rules | `FilmBibleRepository.list_rules_for_project` has no version or supersede filter | Canon drift |
| G04-H | `commit_rules` writes the *new* project version into `expected_project_version` | `film_bible_synthesis/graph.py commit_rules` | Corrupts the version-check field in state |
| G04-I | `human_approval_gate` overwrites `actor_id` (the initiator) with the decider | `graph.py human_approval_gate` | Loses initiator attribution |
| WF-ALL | `propose_*` (candidate + approval creation) is not idempotent; applies to all four graphs | `services/*_review.py` | A redelivered task creates a second approval request |
| WF-ALL | Inconsistent rejection return: storyboard `reject_candidates` returns the current version, script `close_rejected` returns `None` | `storyboard_review.py`, `script_review.py` | Inconsistent API semantics |
| G04-G | The interrupt node lacks the `approval_status != "pending"` guard and raises `TypeError` on non-dict resume; it is inconsistent with G-01…03 | `graph.py human_approval_gate` | Recovery and robustness risk |
