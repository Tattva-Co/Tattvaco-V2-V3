# Release Readiness Checklist

**Doc ID:** TFD-REL-001 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval
**Inputs:** Master Prompt §15, §29 (Definition of Done) · `docs/audit/01`–`10` · all `docs/engineering/*` · ADR-002…ADR-008 · `docs/product/PRD_v1.0.md`

---

## 0. Usage

- A release is ready only when **every gate in its column has evidence linked**. "Evidence" means a CI run URL, a test report, a drill record, a signed approval or a document version. A statement is not evidence. **Never mark a gate passed if its tests have not been executed** (Master Prompt §23).
- **Gate owners:** Eng = engineering lead, Sec = security owner, Prod = product owner, Legal = legal owner (DEC-012), Ops = platform on-call lead.
- **Current position (2026-11-05): pre-alpha.** No gate below is passed. The baseline column records today's facts.

## 1. Foundation gates (required before internal alpha; prerequisite for FD-V1)

| # | Gate | Baseline today | Required evidence | Owner |
|---|---|---|---|---|
| F-01 | G-04 WIP fixed forward (G04-A…G) with regression tests (DEC-010, gate #3) | 5 failed + 1 error in G-04 | CI run: 100 % pass | Eng |
| F-02 | Test suite 100 % green on `main` in CI with isolated test DB (DEC-015) | 47 pass / 5 fail / 1 error, run locally only | CI run link; `TESTING_AND_QA_STRATEGY.md` §6 fixture merged | Eng |
| F-03 | CI pipeline stages 1–8 enforced on PRs | No CI | Branch-protection screenshot + workflow file | Eng |
| F-04 | mypy runnable with ratchet ≤ 321 and decreasing | 321 errors, not enforced | CI mypy job + `mypy-baseline.txt` | Eng |
| F-05 | Authentication (ADR-003, DEC-002 gate #1); header identity test-only | SEC-01 Critical | Negative test "forged header → 401" in staging config | Eng + Sec |
| F-06 | Fail-closed config (SEC-02, SEC-09) | `environment` defaults to development | Config unit tests; startup fails without `ENVIRONMENT` | Eng |
| F-07 | All repo getters scoped; foreign IDs validated (SEC-04) | 3 unscoped getters | Tenant isolation tests per router | Eng |
| F-08 | Version bump locked + unique `(project_id, version_number)` (PERF-06) | Race present | Concurrency test + migration | Eng |
| F-09 | Async-by-default workflows (PERF-01) | `sync_execution=True` | Slice test `test_async_run_202_then_poll` | Eng |
| F-10 | Outbox lease/retry/DLQ + crash tests (ADR-007) | No lease or retry | `test_worker_recovery.py` CI results | Eng |
| F-11 | Streaming upload + magic-byte validation (ADR-008 part 1) | Whole file in memory | Media tests | Eng |
| F-12 | Dockerfile per process + compose `full` profile | No Dockerfile | Image build in CI | Eng |
| F-13 | JSON logs with `request_id` / `workflow_run_id` + redaction test | Text logs | Log sample + redaction test result | Eng |
| F-14 | Generator-mode labels visible in UI (no fake success) | Not shown | Playwright screenshot | Eng + Prod |

## 2. FD-V1 gates (Film Intelligence and Pre-production)

| # | Gate (Master Prompt §29 item) | Required evidence | Owner |
|---|---|---|---|
| V1-G01 | Every FD-V1 P0 requirement in `REQUIREMENT_TO_CODE_TRACEABILITY.md` is `VERIFIED` or explicitly descoped with Prod sign-off (§29.1, 29.17) | Matrix export + slice test results | Prod + Eng |
| V1-G02 | UI handles loading/empty/error/recovery/awaiting-approval states on every FD-V1 screen (§29.2) | Playwright journeys 1–5 green | Eng |
| V1-G03 | API contracts validated against OpenAPI; no breaking change to existing routes without a compatibility note (§29.3) | Schemathesis or contract diff report | Eng |
| V1-G04 | RBAC enforced server-side; the negative authZ matrix covers 100 % of routes (§29.4) | `tests/authz/` report; route-coverage test | Eng + Sec |
| V1-G05 | Tenant and project isolation tested for every getter and foreign ID (§29.5) | Test report | Eng |
| V1-G06 | Screenplay lock: management-only lock, immutable locked versions, impact analysis on revision (ADR-004) | Slice tests TFD-SCR-002/003/010 | Eng + Prod |
| V1-G07 | Versioning and audit correct; audit append-only at DB level (§29.7; SEC-07) | DB grant test; audit coverage test | Eng |
| V1-G08 | AI outputs structured and reviewable; generator mode labelled (§29.8) | Schema validation tests | Eng |
| V1-G09 | AI evaluation measurable: golden sets exist for WF-01..04 with a recorded baseline (§29.9). No quality claims beyond that baseline | Eval report with dataset version | Eng + Prod |
| V1-G10 | Workflow failure and recovery: crash/redelivery tests green for all WFs (§29.10) | CI | Eng |
| V1-G11 | Manual handoff loop: package compile → export (manifest + checksum) → import → map to shot → review, with no provider (§29.11, 29.12) | Slice tests TFD-PKG-002, TFD-INT-001, TFD-OUT-001 | Eng |
| V1-G12 | Consent model and gate in place before any C4 data is stored; DEC-007 and DEC-012 approved, or C4 features flagged off (§29.13) | Legal sign-off **or** flag config evidence | Legal + Prod |
| V1-G13 | Performance measured at the expected tier against NFR-LAT-01..04 and NFR-JOB-01 (§29.15) | k6 report | Eng |
| V1-G14 | Logs and metrics support diagnosis: dashboards 1–3 live; alerts configured (§29.16) | Dashboard links; alert test fire | Ops |
| V1-G15 | Backup and restore drill passed (NFR-DR-03) | `ops/drills/<date>-restore.md` | Ops |
| V1-G16 | 0 Critical / 0 High security findings open (NFR-SEC-04) | Threat model §5 status table | Sec |
| V1-G17 | Docs updated: PRD, IA, ADR register, runbooks reflect the release (§29.17) | Doc versions | Prod + Eng |
| V1-G18 | No critical regression: existing G-01..G-03 slice tests unchanged and green (§29.18, Master §24) | CI | Eng |

## 3. FD-V2 gates (AI Production and External Generation)

All FD-V1 gates must remain green, plus:

| # | Gate | Required evidence | Owner |
|---|---|---|---|
| V2-G01 | Each connected provider has a **verified** capability snapshot (source URLs, date, terms summary) and passed onboarding (TFD-INT-005, DEC-013 gate #7) | Snapshot record + Legal/Prod sign-off | Prod + Legal + Eng |
| V2-G02 | Contract tests per adapter: replay green in CI; one live sandbox run within 7 days of release (Testing §9). Mock results are reported separately | CI + nightly report | Eng |
| V2-G03 | Manual-mode parity: every connected capability is also executable manually (TFD-GEN-008, TFD-INT-008) | Slice tests | Eng |
| V2-G04 | Cost approval + budget gate enforced server-side; over-budget submit blocked (Cost model §4) | Tests + staging demo record | Eng + Prod |
| V2-G05 | Unknown-outcome reconciliation before retry; no duplicate paid submission in crash tests (TFD-GEN-003) | Crash test report | Eng |
| V2-G06 | Consent re-checked at submit; revocation propagation tested end to end (ADR-006) | Slice tests TFD-CNS-004/007 | Eng + Legal |
| V2-G07 | Provider data disclosure shown and acknowledged per connection (TFD-CNS-008) | UI evidence + audit rows | Prod + Legal |
| V2-G08 | DPIA completed for C4 processing (Privacy doc §6) | Signed DPIA | Legal |
| V2-G09 | Presigned media upload, malware scan, quarantine, derivatives (ADR-008); `size_bytes` BigInteger switch complete | Media test report incl. EICAR and 5 GB upload | Eng |
| V2-G10 | SSRF guard on every outbound fetch; webhook signature verification only for documented schemes (Threat model §3.3–3.4) | Security tests | Sec |
| V2-G11 | Production workspace frontend decision executed per ADR-002 (gate #2) for media-heavy screens | Playwright + axe-core report (NFR-A11Y-01) | Prod + Eng |
| V2-G12 | Provider cost dashboard live; budget alerts tested | Dashboard link | Ops |
| V2-G13 | Output inspection against Shot Spec and performance reference (TFD-OUT-002/003); continuity comparison (TFD-CON-007) with a measured precision/recall baseline | Eval report | Eng + Prod |
| V2-G14 | Post handoff package (JSON + CSV manifests, DEC-014) validated by importing into at least one external NLE workflow manually | Validation record | Prod |
| V2-G15 | No V3 scope shipped (NLE, final render, grading, mastering, distribution) | Scope review | Prod |

## 4. Sign-off

| Release | Eng | Sec | Prod | Legal | Ops | Date |
|---|---|---|---|---|---|---|
| Internal alpha (F-gates) | | | | n/a | | |
| FD-V1 (closed pilot) | | | | | | |
| FD-V2 | | | | | | |
