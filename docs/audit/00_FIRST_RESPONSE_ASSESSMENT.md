# 00 — First-Response Assessment (Master Prompt §30, items A–I)

**Doc ID:** TFD-AUDIT-000 · **Date:** 2026-11-05 · **Status:** Delivered before any source-code change
Detailed evidence is in `01`–`10` in this folder. Phase B design documents are in `docs/product`, `docs/architecture`, `docs/engineering`, `docs/release` and `docs/ADRs`.

---

## A. Repository assessment
- **Inspected:** branch `docs/product-evolution-audit` (from `main@b3621cb`), plus the uncommitted G-04 Film Bible WIP (24 modified files and 6 new paths). Per product decision, the WIP was audited but not modified; its diff hash is unchanged before and after this pass.
- **What exists:**
  - A Python modular monolith with three processes: FastAPI API, Streamlit UI (8 views) and an outbox worker.
  - PostgreSQL with 23 application tables (13 core, 6 research, 2 storyboard, 2 film-bible WIP) across 4 linear Alembic revisions.
  - LangGraph with a Postgres checkpointer.
  - A content-addressed local `StorageService`.
- **Workflows present:**
  - G-01 Script Intelligence (verified, deterministic).
  - G-02 Historical Research (verified, mocked generator).
  - G-03 Storyboard (verified, deterministic, from a text brief).
  - G-04 Film Bible (WIP, **broken**).
- **Executed baseline:**
  - pytest: **47 passed / 5 failed / 1 error**. All failures are in G-04.
  - ruff: clean.
  - mypy: 321 errors, so typing is not an enforced gate.
  - Alembic: current = head = `00b7cd57e036` (the WIP migration is already applied locally).

## B. Verified implementation inventory
Full matrix: `02_FEATURE_IMPLEMENTATION_MATRIX.md`.

| Bucket | Items |
|---|---|
| Implemented and verified (locally, deterministic or mocked intelligence) | Script intelligence; historical research workflow; storyboard workflow; single-tier review and approval; candidate → canonical → version → audit lifecycle; org-level tenant isolation for projects, approvals and runs; immutable storage; G-01 checkpoint recovery |
| Partial | Project management, asset ingestion (text only), character, location and shot concepts (generic entities and panels), versions and audit (race condition, no branches) |
| Mocked or placeholder | Research investigator; film-bible synthesizer; storyboard lens notes; "Higgsfield manual_export" (config only) |
| Broken | G-04 Film Bible: defects G04-A (partial approval approves all), G04-B (missing repository method), G04-C (teardown FK leak), plus D/E/F/G |
| Missing | Real auth/RBAC, locked screenplay, suggestions workspace, timeline, all bibles beyond rules, physical identity, costumes and props, cinematography, sequences and shots, continuity, Context Resolver, AI Director, Shot Spec, prompt compiler, packages, manual export and import, observability, and **all 25 V2 items** (generation job tracking is only scaffolded) |
| New families absent from code and from PRD v0.9 | Production mode hierarchy, digital doubles and avatars, performer consent, capture planning, footage ingestion, voice and localisation, format templates, post handoff |

## C. Current architecture assessment
- **Good, and should remain:**
  - Modular monolith with service and repository layering.
  - DB-derived org identity; scoped repositories with no existence oracle.
  - Candidate → approval → canonical lifecycle with expected-version checks.
  - The approval decision is committed before graph resume.
  - PostgreSQL as canonical truth, with LangGraph checkpoints as execution state only.
  - Postgres outbox with `SKIP LOCKED`; content-addressed immutable storage behind an interface.
  - Alembic with a drift test; the `StorageService` port.
- **Must change:**
  - Authentication (header impersonation, dev fallback on by default).
  - RBAC and project membership.
  - Unscoped getters and cross-tenant foreign-ID validation.
  - Version-bump locking plus a unique constraint.
  - Async-by-default workflows.
  - Worker lease, retry and dead-letter, with re-delivery resuming from the checkpoint.
  - Streaming, signature-checked uploads and real document parsing.
  - A ModelGateway before any real AI.
  - A shared approval-gate helper across the WF graphs.
  - CI, containers, observability and test-DB isolation.
- **Would add unnecessary complexity now:**
  - Microservices or Kubernetes.
  - A separate queue broker before measured need.
  - A graph database.
  - pgvector embeddings without an evaluated retrieval need.
  - A multi-agent fleet.
  - Rewriting the three working slices.
  - A frontend migration before the V2 UX is defined.

## D. Product evolution assessment
PRD v0.9 covers a **fully-AI, pre-production-to-handoff** product. Mapping to the Master Prompt:

| Master Prompt area | PRD v0.9 coverage | New requirements family |
|---|---|---|
| §4 Two equal modes, mode at 5 levels | Live action listed as out of scope | TFD-HYB, project/sequence/scene/character/shot mode inheritance |
| §5 Locked screenplay and 3 workflows | Partial (canon/approval concept) | TFD-SCR: versions, lock, suggestions workspace, director revisions, management approval, impact analysis |
| §6 Character identity, digital humans, measurements, consent | Character bible only; consent generic | TFD-CHR, TFD-DH, TFD-PHY, TFD-CNS |
| §7 Cinematography (physical + virtual) | Persona + Film Bible principles | TFD-CIN: extensible camera spec, actual vs creative-target provenance |
| §8 On-set / chroma / footage ingestion | Optional footage inspection | TFD-HYB: capture plans, manifests, ingestion analysis |
| §9 Voice / dialogue / lip-sync / dubbing | Absent | TFD-VOC |
| §10 Production formats | Absent | TFD-FMT: templates and output profiles |
| §11 Continuity dimensions + 9-state model | Continuity graph (less specific) | TFD-CON |
| §12 Connected + manual, registry, recommendation | Higgsfield + manual fallback + capability registry | TFD-INT, TFD-GEN: multi-provider registry, verification register, recommendation engine |
| §14 Post-production boundary | Out of scope | TFD-POST: manifests, handoff packages; interchange formats only once validated |

These are captured in `docs/product/PRD_v1.0.md` (Phase B).

## E. Database impact
Detail: `05_DATABASE_AND_MIGRATION_AUDIT.md` and `docs/architecture/DATABASE_DESIGN_AND_ERD.md`.
- **Extend:**
  - `users`/`organizations`: memberships.
  - `projects`: format, mode, delivery profile.
  - `scenes`: screenplay_version_id, production_mode, organization_id.
  - `entities`: legacy link to `characters`.
  - `assets`: processing state, rights, retention, provenance.
  - `approval_requests`: generalized scopes and levels.
  - `outbox_tasks`: lease, retry, dead-letter.
  - `project_versions`: unique constraint, organization_id.
  - `storyboard_panels`: frame mapping.
  - `research_*`: locators, timeline.
- **New:** screenplay governance, sequences, shots and dialogue, the character and digital-human group, consent, the costume, prop and environment group, the cinematography and capture group, asset derivatives and lineage, continuity, context and AI-run records, and the provider/package/job/import/review group.
- **Migrations:**
  - Additive only, following expand → backfill → verify → switch → contract.
  - First migration: add the unique `(project_id, version_number)` constraint after a duplicate check, plus `organization_id` backfills.
- **Protection:**
  - pg_dump before any shared-environment migration.
  - Never edit or delete an applied revision.
  - Upgrade/downgrade round-trip in CI.
  - Row-count and checksum reconciliation for backfills.
  - Legacy routes kept behind adapters until parity.

## F. Technical documentation
- **Exists:** PRD v0.9, IA v1.0, Wireframe v1.0, Greenfield Addendum v1.1, ADR-001 (two diverging copies), Readiness README, Build Prompt, SOURCE_OF_TRUTH_INDEX, GREENFIELD_BUILD_PLAN, OPEN_DECISIONS.
- **Updated in this pass:** change notes only; nothing deleted or rewritten. GREENFIELD_BUILD_PLAN statuses, OPEN_DECISIONS (pointer to DEC-009+), SOURCE_OF_TRUTH_INDEX (new precedence and documents).
- **Created in this pass:**
  - `docs/audit/00–10`.
  - `docs/product`: PRD v1.0, roadmap, journeys, IA, screen inventory, acceptance criteria.
  - `docs/architecture`: 10 documents.
  - `docs/engineering`: 11 documents.
  - `docs/release`: 4 documents.
  - ADR-002 to ADR-008.

## G. Security and scalability: critical risks
1. **SEC-01 / SEC-02 (critical).** Identity is an unauthenticated header. The dev fallback is on by default and can bind to an arbitrary org.
2. **SEC-03 (high).** There is no authorization. Any org member can approve or reject anything, and there is no management authority for screenplay lock.
3. **SEC-04 (high).** Unscoped getters and unvalidated foreign IDs allow cross-tenant references.
4. **SEC-05 (high).** Uploads are buffered in memory with client-trusted MIME, and there is no scanning. This blocks video and footage work.
5. **SEC-12.** There is no consent model. It is a blocker for any digital-double, likeness or voice feature.
6. **PERF-01/04.** Synchronous LangGraph runs in HTTP requests. The worker has no lease, retry or dead-letter, so it is not horizontally safe against crashes.
7. **PERF-06.** A version-number race exists in 3 review services.
8. **Load balancing and caching.** Not applicable yet, because there is no deployment. API replicas are already stateless apart from the in-request sync runs. Redis and a CDN are not justified until media previews and SSE status exist.
9. **External providers.** None are connected. The risks are future ones: terms violations (Midjourney automation), unknown job outcomes, uncontrolled spend, and consent leakage to providers.

## H. Recommended implementation roadmap
Phases C onward. **None of this starts until the approval gates are decided.**

| # | Task | P | Size | Depends on | Affected modules | Acceptance criteria | Test plan | Risks | Rollback |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Fix G-04 (A/B/C, plus D gated behind approval) | P0 | S | Gate 3 | `workflows/film_bible_synthesis`, `services/film_bible*`, `tests/support.py` | All 6 G-04 tests pass; partial approval commits only the selected rules | Existing 6 tests plus a regression for each defect | Low | Revert commit; migration unchanged |
| 2 | Test DB isolation + CI (ruff, pytest, alembic round-trip) | P0 | M | — | `tests/conftest.py`, `.github/workflows` | CI green on PRs; dev DB untouched by tests | CI run | Low | Disable workflow |
| 3 | Real authentication + fail-closed environment | P0 | M | Gate 1 | `apps/api/dependencies.py`, `services/identity.py`, `core/config.py`, UI client | No request authenticates via header outside `test`; JWT verified | Authn negative tests | Locks out the local UI until login exists | Feature flag `AUTH_MODE` |
| 4 | RBAC + project membership + scoped getters + foreign-ID validation | P0 | L | #3 | repositories, services, new `memberships` migration | Negative authZ matrix passes for every route | Matrix test per router | Backfill errors | Additive migration; downgrade tested |
| 5 | Version-bump lock + unique constraint + org_id backfills | P0 | M | #2 | `*_review.py`, migration | Concurrent-approval test yields unique versions | Concurrency test | Existing duplicate rows | Pre-check query; downgrade |
| 6 | Async-by-default + worker lease/retry/DLQ + resume-from-checkpoint | P0 | L | #2 | `apps/worker`, `outbox_tasks`, services, UI task tray | Kill-worker test recovers; no duplicate candidates | Crash and redelivery tests | Behaviour change in the UI | Flag `sync_execution` default |
| 7 | Streaming upload, signature sniffing, real PDF/DOCX/Fountain/FDX parsing, derivatives | P0 | L | Gate 5 | `routers/assets.py`, `storage`, new `asset_derivatives` | 2 GB upload with flat memory; mismatched signature rejected | Media and malicious-file tests | Parser libraries | Additive |
| 8 | ModelGateway + Context Resolver (mock adapter labelled) + shared approval-gate helper | P0 | L | Gate 4 | `packages/ai/*` (new), WF graphs | All generators behind the gateway; mode shown in the UI | Unit + golden set skeleton | Refactor regressions | Keep old generator as the mock adapter |
| 9 | Screenplay governance (versions, lock, suggestions, revision, management approval, impact) | P0 | XL | #4 | new module, `scenes` extension | TFD-SCR acceptance criteria | Vertical-slice test | Scope creep | Additive |
| 10 | Character/identity/physical profile + consent model | P0 | XL | #4, Gate 6 | new modules | Consent enforcement points block unauthorised use | Consent negative tests | Legal dependency | Additive |
| 11 | Costume/prop/environment bibles; cinematography bible + camera spec | P0 | L | #8 | new modules | TFD-CST/PRP/ENV/CIN acceptance criteria | Slices | — | Additive |
| 12 | Sequences/shots/production mode; continuity rules and findings | P0 | XL | #9, #11 | new modules | Mode inheritance; continuity states | Slices | — | Additive |
| 13 | Shot Spec + prompt compiler + package export + manual import loop | P0 | XL | #12 | new `packages/integration` | End-to-end manual loop with all providers disabled | E2E | — | Additive |
| 14 | Observability (JSON logs, OTel, readiness) + Dockerfiles | P1 | M | #2 | `core/logging.py`, `apps/*` | Trace across API → worker | Smoke | — | — |
| 15 | V2: provider registry + first verified adapter + jobs/attempts/cost | P1 | XL | #13, Gate 7 | `packages/integration` | Contract tests; spend approval enforced | Contract + canary | Provider terms | Flag per provider |
| 16 | V2: capture planning, footage ingestion, digital human, voice, lip-sync, output inspection, handoff package | P1 | XL | #15, #10 | multiple | Per PRD v1.0 | Slices | Large scope | Flags |
| 17 | Frontend production workspace (if ADR-002 approved) | P1 | XL | Gate 2 | new app | Parity with Streamlit for V1 flows | Playwright | Duplicate UI cost | Keep Streamlit |

## I. Approval gates
These decisions genuinely require you. Each comes with a recommendation.

| Gate | Decision | Recommendation |
|---|---|---|
| 1 | Auth provider (DEC-002) | Any OIDC provider behind an `AuthProvider` port. Real auth is a P0 blocker before any shared or staging use. |
| 2 | Frontend (DEC-009, ADR-002) | Keep Streamlit for FD-V1 alpha. Decide the production frontend (React/Next.js recommended for V2 media workspaces) before the V2 UX freeze. Do not migrate now. |
| 3 | G-04 WIP (DEC-010) | Fix forward as the first Phase C task; do not discard (its migration is already applied locally). |
| 4 | Model gateway / LLM (DEC-004) | Build the gateway and golden sets first; choose a provider by evaluation, not by preference. |
| 5 | Object storage + media pipeline (DEC-003) | S3-compatible behind the existing `StorageService`; presigned streaming uploads. |
| 6 | Consent/likeness policy owner (DEC-012, DEC-007) | Legal owns the consent template and retention policy. No likeness or voice data is stored until it exists. |
| 7 | First connected provider (DEC-013) | One image provider with an official API, after terms and legal review. Midjourney stays manual-only. |

**Nothing beyond documentation was changed in this pass.** No code, migrations, DB schema, commits or framework changes.
