# 10 — Document Conflict and Decision Register

**Doc ID:** TFD-AUDIT-010 · **Audit date:** 2026-11-05
**Precedence (Master Prompt §2.3):**
1. Explicit decisions in the Master Execution Prompt
2. Product Evolution & Gap Report v1.0
3. Latest approved PRD / strategy
4. Approved ADRs
5. Current architecture / engineering docs
6. Repository implementation
7. New evidence-backed recommendations

Nothing below silently overwrites a prior decision. Each conflict records a recommended resolution and its status.

## 1. Document-vs-document conflicts

| ID | Conflict | Sources | Consequence | Recommended resolution | Status |
|---|---|---|---|---|---|
| CON-01 | Frontend: PRD v0.9 §10 recommends Next.js/React/TS; ADR-001 + SOURCE_OF_TRUTH_INDEX select Streamlit | PRD v0.9; `docs/ADRs/ADR-001`; `docs/product/Tattva_ADR_001…` | Ambiguous UI investment | ADR-002 (Phase B): Streamlit = internal alpha/control surface for V1; production workspace frontend decided by approval gate | OPEN, approval gate #2 |
| CON-02 | Two divergent ADR-001 copies: `docs/ADRs/` says "Approved, PRD *is* amended"; `docs/product/` copy says "Proposed, PRD *should* be amended" | both ADR-001 files | Unclear authority | Treat `docs/ADRs/ADR-001` as canonical; mark the `docs/product` copy superseded via change note | Recommended |
| CON-03 | "G-0x" collision: IA/Wireframe G-01…G-08 = global screens; Addendum/code G-01…G-11 = graphs | IA v1.0, Wireframe v1.0, Addendum v1.1, `apps/ui` labels | Requirements and traceability ambiguity | New IDs: screens `S-<area>-nn`, graphs `WF-01…`; keep legacy IDs as aliases in the traceability matrix | Recommended (DEC-011) |
| CON-04 | Screen count: PRD 26, IA 44, Master Prompt §25 proposes 25 workspace groups; code has 8 views | PRD, IA, Master Prompt | No canonical UX baseline | Phase B `INFORMATION_ARCHITECTURE.md` defines one inventory (workspace groups → screens), mapped to IA IDs | Phase B |
| CON-05 | Status labels: Build Plan / Index say "Approved"; PRD, IA, Wireframe, Addendum say draft/proposed | all | Unclear what is signed | Master Prompt + Gap Report now top precedence; PRD v1.0 (Phase B) becomes the scope baseline after approval | Recommended |
| CON-06 | Decision numbering: PRD `FD-DEC-xxx` vs OPEN_DECISIONS `DEC-001…008` vs Gap Report FD-FR-001…050 | PRD, OPEN_DECISIONS, Gap Report | Duplicated registers | Single register: this file plus `docs/engineering/ADR_REGISTER.md`; requirement IDs `TFD-<AREA>-nnn` with FD-FR aliases | Recommended |
| CON-07 | Missing referenced doc: `Tattava_Copilot_Architecture_Blueprint_Revised_v2.0` cited by SOURCE_OF_TRUTH_INDEX | Index | Broken reference | Mark as "external, not in repo"; obtain or drop | OPEN (owner: product) |
| CON-08 | Scope expansion: PRD v0.9 treats live-action as out of scope (≈l.295) and has no digital humans; the Master Prompt makes hybrid live-action + AI an equal mode | PRD v0.9 vs Master Prompt §4 | PRD is out of date | Master Prompt wins (precedence 1); PRD v1.0 incorporates it | Resolved by precedence |
| CON-09 | PRD release language: Gap Report §2.3 warns that Film Director V1/V2/V3 must not redefine wider "Tattava Copilot" V1 | Gap Report | Roadmap confusion across products | Label releases "FD-V1/FD-V2/FD-V3" in PRD v1.0 | Recommended |

## 2. Document-vs-code conflicts

| ID | Conflict | Evidence | Resolution |
|---|---|---|---|
| CODE-01 | Build Plan says M1 in progress, M2–M4 "ready to build", G-02+ "Future"; code has M2–M4 done plus G-02, G-03 and G-04 (WIP) | `GREENFIELD_BUILD_PLAN.md` vs git log | Update statuses with a change note (Phase A step 4) |
| CODE-02 | DEC-002 lists `X-Org-ID` and `X-Project-ID` headers; code uses only `X-Actor-ID` (better: org is derived from the DB) | `OPEN_DECISIONS.md` vs `dependencies.py` | Amend DEC-002 text to match code; supersede with real auth |
| CODE-03 | DEC-004 / Build Plan reference `ModelGateway` and `test_model_gateway_mock.py`; neither exists | Build Plan §4 | Mark NOT_IMPL; build in Phase C/D |
| CODE-04 | Build Plan requires async 202 + polling from Streamlit; code defaults to sync | `schemas.py` `sync_execution=True` | Fix in Phase C (async-by-default) |
| CODE-05 | PRD storyboard = image/PDF panel ingestion; code = text-brief generation | `storyboard_intelligence/aligner.py` | Classify G-03 as PARTIAL against PRD; panel ingestion in V1 backlog |
| CODE-06 | Build Plan test matrix lists `tests/authorization/test_tenant_isolation.py`; the file no longer exists (moved to `tests/api/test_tenant_isolation_api.py`; stale entry in `.pytest_cache`) | Build Plan §4 | Update path |
| CODE-08 | SOURCE_OF_TRUTH_INDEX states that a "manual export/import package format" and an "S3-compatible adapter interface" are implemented, and that the auth boundary uses "context tokens" | Code: Higgsfield is config only; only `LocalFileSystemStorageService` exists; auth is an unauthenticated header | Change note appended to the Index (2026-11-05) |
| CODE-07 | ADR-001 invariant "AI output is only a candidate": manual research/film-bible POSTs write canonical rows directly | `ResearchService.create_*`, `FilmBibleService.create_rule` | Treat as defect SEC-06 |

## 3. Gap Report v1.0 vs current code (Gap Report audited `44346a0`)

| Gap Report finding | Current state (`b3621cb` + WIP) | Verdict |
|---|---|---|
| "Overly broad CORS: all origins, credentials, methods, headers" | Allowlist, no credentials, GET/POST, 2 headers | **Fixed** |
| "Routes accept actor_id/organization_id in bodies" | `IdentityService` derives org from DB; actor from `X-Actor-ID` header | **Partially fixed:** org is no longer client-supplied; actor is still unauthenticated |
| "Project get/list use direct ORM queries; scoped repos not used" | Projects/approvals/runs use `get_scoped` | **Mostly fixed;** research/film-bible getters remain unscoped |
| "One LangGraph workflow (G-01)" | G-01, G-02, G-03 committed; G-04 WIP | **Outdated** |
| "Six Streamlit destinations" | Eight views | **Outdated** |
| "Upload reads full file in memory; MIME/size not enforced" | Size enforced; still in memory; MIME still client-trusted | **Partially fixed** |
| "No provider implementation" | Still none | **Still valid** |
| "No CI" | Still none | **Still valid** |
| "Build plan statuses stale" | Still stale | **Still valid** |
| "Parser assumes uppercase cues; no golden set" | Unchanged | **Still valid** |

## 4. Decision register (continues OPEN_DECISIONS DEC-001…008)

| ID | Decision | Recommendation | Approver | Status |
|---|---|---|---|---|
| DEC-001 | Managed PostgreSQL | Defer to staging; any managed PG16 with pgvector + PITR | Eng | Open |
| DEC-002 | Auth provider | Adopt an OIDC provider behind an `AuthProvider` port; JWT verification in `get_actor`; header identity test-only | Product + Eng + Security | **Approval gate #1** |
| DEC-003 | Object storage | S3-compatible adapter (S3/R2/MinIO) behind the existing `StorageService`; presigned uploads | Eng | **Approval gate #5** |
| DEC-004 | Model gateway / LLM | Build `ModelGateway` + mock adapter first; provider choice after an eval spike on golden sets | Product + Eng | **Approval gate #4** |
| DEC-005 | Queue | Keep the Postgres outbox; add lease/retry/DLQ; revisit at a measured throughput ceiling | Eng | Recommended (ADR-007) |
| DEC-006 | Higgsfield | Manual package mode first; API and MCP as separate adapters after contract verification | Product + Legal | Open |
| DEC-007 | Retention & privacy | Policy required before any performer likeness/voice data is stored | Product + Legal | **Blocking for digital-human work** |
| DEC-008 | Hosting | Containers (Dockerfile per process) on a managed container platform; no Kubernetes until justified | Eng | Open |
| DEC-009 | Frontend for production workspace | Streamlit for V1 alpha; decide production frontend before V2 UX freeze (ADR-002) | Product + Eng | **Approval gate #2** |
| DEC-010 | G-04 WIP disposition | Fix forward (G04-A/B/C + tests) as first Phase C task; do not discard (migration already applied locally) | Eng | **Approval gate #3** |
| DEC-011 | ID scheme for screens/graphs/requirements | `S-*` screens, `WF-*` graphs, `TFD-<AREA>-nnn` requirements; legacy IDs as aliases | Product | Recommended |
| DEC-012 | Consent & likeness policy owner and template | Legal-owned consent template; product models purpose-specific, versioned, revocable consent records | Legal + Product | **Approval gate #6** |
| DEC-013 | First connected provider pilot (V2) | One image provider with an official API after terms/legal review; Midjourney stays manual-only | Product + Legal + Eng | **Approval gate #7** |
| DEC-014 | Post-production interchange formats | JSON + CSV manifests first; OTIO only after a validated round-trip in Resolve/Premiere | Product | Recommended |
| DEC-015 | Test database isolation | Dedicated per-session test DB | Eng | Recommended |
| DEC-016 | Retrieval index / embedding model (pgvector) | None in FD-V1; enable per purpose only after an evaluation shows it beats structured selection | Eng | Recommended |
| DEC-017 | Facial embeddings / biometric templates | None in FD-V1/V2; identity checks stay human side-by-side review | Product + Legal | Recommended |
| DEC-018 | Media probe toolchain (ffprobe/FFmpeg) | Pinned LGPL build in the worker image, subject to licence review | Eng + Legal | Recommended |
| DEC-019 | Postgres row-level security as a second tenant-isolation layer | FD-V2, after `organization_id` has been backfilled on every tenant table | Eng + Security | Recommended |
| DEC-020 | Expected-version scope | Replace the project-wide `expected_project_version` check with a fingerprint of the inputs each run actually read, so unrelated approvals stop conflicting | Eng | Recommended |
| DEC-021 | Default `production_mode` for existing projects | Backfill `fully_ai`, and ask project owners to confirm | Product | Recommended |
| DEC-022 | Malware scanning engine for uploads | See `docs/engineering/SECURITY_THREAT_MODEL.md` | Eng + Security | Open |
| DEC-023 | Observability backend | See `docs/engineering/OBSERVABILITY_AND_MONITORING.md` | Eng | Open |
| DEC-024 | Feature-flag mechanism | See `docs/engineering/DEPLOYMENT_AND_DEVOPS.md` | Eng | Open |
| DEC-025 | Budget-gate defaults and who approves cost | See `docs/engineering/COST_AND_CAPACITY_MODEL.md` | Product + Finance | Open |
| DEC-026 | Pilot support hours and availability tier | See `docs/release/PRODUCTION_LAUNCH_PLAN.md` | Product + Ops | Open |
| DEC-027 | Role and capability matrix, including who holds management authority over the locked screenplay | **Implemented in milestone C5** (2026-11-06): 6 role templates (`management`, `director`, `producer`, `crew_editor`, `reviewer`, `viewer`) and 17 capabilities (`packages/domain/capabilities.py`), deny-by-default, org-owner bypass. `management` holds `screenplay.approve_lock`; no other template does. **No longer a blocker for screenplay lock** (D2), which can now gate on that capability directly. | Product + Eng | **Done** |
| DEC-028 | Pilot productions, format-template default values, pilot acceptance thresholds | See `docs/product/PRODUCT_ROADMAP.md` | Product | Open |
| DEC-029 | Creative branches | Defer; remove the hardcoded "Branch: main" label from the UI | Product | Recommended |
| DEC-030 | `apps/web` dev-tooling vulnerabilities not patched in GW2 | `npm audit` (2026-11-06, re-checked after adding the typescript-eslint toolchain) flags 16 advisories: react-router 6.x (open redirect via backslash in `<Link>`/`useNavigate`, low practical risk here: no attacker-controlled redirect target is ever passed to navigation), vitest/tinypool/`@vitest/mocker` (dev-only test runner, incl. 2 "critical" RCE advisories that require a locally-running Vitest UI server we never start), typescript-eslint/minimatch (lint-time only), esbuild/vite (dev-server-only). Fixes require major bumps (React Router 7, Vitest 5) with real API migration. Defer to a dedicated upgrade milestone before GA; re-run `npm audit` at that gate | Eng | Accepted pre-launch risk |
| DEC-031 | Playwright E2E suite (`apps/web/e2e/`) runs locally only, not in CI | It needs a live API process plus Postgres running alongside the Vite dev server (`apps/web/playwright.config.ts` starts both as `webServer` entries against the `_test` database on the local docker-compose Postgres instance). Wiring an equivalent 3-process stack (Postgres service container + uvicorn + vite) into GitHub Actions is real but separable work. The `frontend` CI job runs typecheck/lint/Vitest only; `npm run e2e` is documented as a local-only command until a dedicated CI job is added | Eng | Accepted gap, revisit at F2 (production readiness) |
| DEC-032 | **Bug found & fixed in GW2**: a plain org 'member' creating their own project could never complete JRN-01 (Guided Workspace section 1), which gates the entire rest of the journey | `ProjectService.create` (`packages/services/projects.py`) auto-granted the creator the `director` role template, but every JRN-01 group has `act_capability: project.admin`, which `director` lacks (only `management` has it, and the creator never gets `management`). This was invisible to every prior GW1 test because `tests/support.py::create_tenant()` always makes its actor an org *owner*, which bypasses `project_memberships` entirely -- no test exercised "a non-owner creates and then works their own project" until building the GW2 E2E flow surfaced it. Fixed by adding a new `project_owner` role template (`packages/domain/capabilities.py`: every project-scoped capability except the org-level `project.create`), granting it instead of `director` on project creation, and backfilling existing data (migration `a9fb5bf54591`: seeds `project_owner` per existing org, retargets each project's creator's own `director` row to `project_owner`, leaves every other member's `director` grant alone). Regression test: `tests/api/test_journey_authorization.py::test_a_plain_member_project_creator_can_complete_the_first_required_journey_section` | Eng | Fixed; verified by migration round-trip with seeded data (upgrade retargets, downgrade reverts) and the new regression test |
| DEC-033 | GW3's Playwright parity suite (`apps/web/e2e/guided-workspace.spec.ts`, `studio-tools-pipeline.spec.ts`) is written but **not executed** in this environment | This sandbox has no network access to `cdn.playwright.dev` / `playwright.download.prss.microsoft.com` (DNS resolution fails: `ENOTFOUND`), so `npx playwright install chromium` cannot fetch a browser binary here -- confirmed after a ~45-minute wait, including contention on a second, concurrently-running session's own install attempt sharing the same `~/Library/Caches/ms-playwright` lock. Verification for GW3 instead rests on: TypeScript strict + ESLint clean, 39 Vitest/Testing-Library tests exercising every tool's real logic against mocked calls whose shapes were cross-checked field-by-field against the actual Pydantic response models and FastAPI route signatures (not guessed), and a full manual trace of every new endpoint against its router source. Per "existing functionality protection", `apps/ui` (Streamlit) is deliberately NOT deleted until the Playwright suite actually runs green on a networked machine or in CI -- run `npm run e2e` there before that deletion gate | Eng | Open: run the E2E suite on a networked machine/CI, then proceed to the `apps/ui` deletion gate |

**Workflow ID allocation:**
- WF-01…WF-11 are mapped from legacy G-01…G-11.
- New workflows: WF-12 Capture Planning, WF-13 Footage Ingestion & Analysis, WF-14 Screenplay Change Impact, WF-15 Screenplay Suggestions.
- `AI_SYSTEM_ARCHITECTURE.md` owns this numbering, and the product docs were remapped to match on 2026-11-05.

---

## Change Note — 2026-11-06

All gates and recommended decisions were **approved by the product owner**. Decisions, external dependencies and the resolution of CON-04 are recorded in `11_APPROVAL_GATE_DECISIONS.md`. The new UX baseline is `docs/product/ux/guided-workspace-v1.0/` (Guided Workspace UX Strategy v1.0 and Wireframe v1.1). It is the canonical navigation model, and the screens in `INFORMATION_ARCHITECTURE.md` map beneath its 10 sections.
