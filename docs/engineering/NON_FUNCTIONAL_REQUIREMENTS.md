# Non-Functional Requirements

**Doc ID:** TFD-ENG-001 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval
**Inputs:** Master Prompt §20.6, §21, §23, §29 · `docs/audit/03`, `05`, `08`, `09` · `packages/core/config.py` · `apps/worker/worker.py` · `apps/api/routers/assets.py` · `SCALABILITY_PERFORMANCE_CAPACITY_PLAN.md` (workload tiers referenced here)

---

## 0. How to read this document

- **Nothing has been measured.** Audit `08` §2 states that no load, stress or soak test exists and that no performance figure can be claimed. Every "Current" cell below is therefore either `NOT MEASURED` or a **configured value** (a setting in code, which is not a measurement). The only timing that has been observed is the test-suite wall clock (6.8 s for 53 tests, `docs/audit/01` §5). It says nothing about production latency.
- Every target states the **assumption** it rests on. If the assumption changes, the target is re-derived rather than kept.
- Targets apply at the **expected** workload tier defined in `SCALABILITY_PERFORMANCE_CAPACITY_PLAN.md` §6, unless a row says otherwise.
- Each NFR has an ID `NFR-<group>-nn`. Requirement rows in `REQUIREMENT_TO_CODE_TRACEABILITY.md` reference them.
- **Phase:** `A` = required for internal alpha. `P` = required for closed pilot. `GA` = required for general availability (see `docs/release/PRODUCTION_LAUNCH_PLAN.md`).

## 1. Latency (API)

| ID | Metric | Target | Current | Assumption behind the number | Phase |
|---|---|---|---|---|---|
| NFR-LAT-01 | p95 latency, authenticated read (`GET` single object or a page of ≤ 50 rows) | ≤ 300 ms server-side; p99 ≤ 800 ms | NOT MEASURED | Same-region DB; indexed `(project_id, created_at)` lookups (`docs/audit/05` §2); cursor pagination exists (PERF-05 fixed); no N+1. 300 ms leaves headroom inside a 1 s perceived-response budget for the browser render | P |
| NFR-LAT-02 | p95 latency, synchronous command without AI (create project, record decision, upload metadata commit) | ≤ 500 ms | NOT MEASURED | One transaction, ≤ 10 statements, row lock held only for the version bump (`docs/audit/03` §7) | P |
| NFR-LAT-03 | p95 latency to accept a workflow start (`202` + `workflow_run_id`) | ≤ 300 ms | NOT MEASURED. Today the default is `sync_execution=True` (`apps/api/schemas.py`), so the request blocks for the whole graph | Async-by-default (PERF-01 / CODE-04 fixed): the request only inserts `workflow_runs` + `outbox_tasks` in one transaction | A |
| NFR-LAT-04 | p95 latency, approval decision → `200` (decision committed) | ≤ 500 ms; graph resume continues asynchronously | NOT MEASURED. Today `decide()` resumes the graph inside the request | Decision is committed before resume (ADR-001 invariant 4, already true). Resume moves to the worker | P |
| NFR-LAT-05 | Health `GET /health` (liveness) and `GET /ready` (readiness) | ≤ 50 ms liveness; ≤ 200 ms readiness | NOT MEASURED; `/ready` does not exist | Liveness does no I/O. Readiness checks DB `SELECT 1` and the storage adapter | A |
| NFR-LAT-06 | Time to first status update after a workflow state change, as seen in the UI | ≤ 3 s p95 | NOT MEASURED. The Streamlit UI does not poll (`docs/audit/04` §1) | SSE push or 2 s polling of `GET /workflow-runs/{id}` (see capacity plan §2.6) | P |

## 2. Background job latency and throughput

| ID | Metric | Target | Current | Assumption | Phase |
|---|---|---|---|---|---|
| NFR-JOB-01 | Pickup latency: `outbox_tasks.created_at` → claimed (p95, with an idle worker in the pool) | ≤ 5 s | NOT MEASURED. Configured poll interval is 1.0 s (`worker_poll_interval_seconds`) | One poll interval plus claim transaction plus margin for a busy pool. Will be replaced by `LISTEN/NOTIFY` wake-ups only if this target is missed (capacity plan §4) | A |
| NFR-JOB-02 | Deterministic graph (WF-01…WF-04 with the mock generators) end-to-end to `awaiting_approval` | ≤ 30 s p95 | NOT MEASURED | Deterministic Python with no network calls; dominant cost is DB writes of candidates. The 30 s value is a ceiling chosen to detect regressions, not a forecast | A |
| NFR-JOB-03 | LLM-backed graph end-to-end | **OPEN — DEC-004.** Set after the model-gateway eval spike. Hard per-task timeout 15 min | NOT APPLICABLE (no LLM exists, `docs/audit/06` §1) | Provider latency cannot be assumed (brief: do not invent provider capabilities) | P |
| NFR-JOB-04 | Stuck-task recovery: a task held by a crashed worker becomes claimable again | ≤ lease length + one sweep interval (default 5 min + 30 s) | **Never.** No lease exists (`docs/audit/03` §8) | Lease column `lease_expires_at` and heartbeat (ADR-007) | A |
| NFR-JOB-05 | Duplicate side effects on redelivery | 0 duplicate candidate sets, 0 duplicate paid provider submissions | **Fails today**: re-execution restarts from START (`docs/audit/06` §3) | Resume from checkpoint when one exists; `dedupe_key`; provider-side idempotency only where verified | A (candidates) / FD-V2 (provider) |
| NFR-JOB-06 | Approval-to-canonical: decision committed → canonical rows and `project_versions` row written | ≤ 10 s p95 | NOT MEASURED | Resume enqueued as an outbox task with the same pickup latency as NFR-JOB-01 | P |

## 3. Availability and durability

| ID | Metric | Target | Current | Assumption | Phase |
|---|---|---|---|---|---|
| NFR-AV-01 | API availability (successful `GET /ready` from an external probe, monthly) | Pilot: 99.5 % within agreed support hours. GA: 99.9 % all hours. **OPEN — DEC-026** (support model) | NOT MEASURED; there is no deployment | 99.5 % ≈ 3.6 h/month of allowed downtime. That is achievable with one region, managed PG with automatic failover, ≥ 2 API replicas, and rolling deploys. 99.9 % (≈ 43 min/month) needs on-call cover outside business hours | P / GA |
| NFR-AV-02 | Worker availability: queue not draining for > 10 min while tasks are pending | 0 occurrences per month outside maintenance | NOT MEASURED | ≥ 2 worker replicas per pool; alert on `tattva_outbox_oldest_pending_age_seconds` (Observability §3) | P |
| NFR-DUR-01 | Committed canonical DB data lost on a single-node failure | 0 | Local Docker volume only | Managed PG16 with synchronous standby or storage-level replication (DEC-001) | P |
| NFR-DUR-02 | Original asset bytes lost or altered after commit | 0; every original verifiable by `assets.checksum_sha256` | Local filesystem, write-once with a path guard (`packages/storage/service.py`); no replication | S3-compatible storage with versioning and, for originals, object lock (ADR-008, DEC-003) | P |
| NFR-DUR-03 | DB-row ↔ object consistency: asset rows with missing objects, or objects with no row | 0 rows with missing objects. Orphan objects are detected within 24 h | No reconciliation exists | Daily reconciliation job (`BACKUP_AND_DISASTER_RECOVERY.md` §4) | P |

## 4. Recovery (RPO / RTO)

| ID | Scope | RPO | RTO | Current | Assumption | Phase |
|---|---|---|---|---|---|---|
| NFR-DR-01 | Canonical PostgreSQL (app tables + LangGraph checkpoint tables) | Pilot ≤ 15 min; GA ≤ 5 min | Pilot ≤ 4 h; GA ≤ 1 h | No backups configured | Managed PITR with WAL archiving (RPO bounded by archive interval). RTO covers provisioning a restored instance, reconciliation, and smoke tests | P / GA |
| NFR-DR-02 | Object storage (original assets) | 0 for committed objects | ≤ 4 h (same as DB; assets are useless without rows) | No replication | Provider durability plus versioning; the row is written only after `put` succeeds | P |
| NFR-DR-03 | Restore drill | Executed and passed once before pilot, then quarterly | Never executed | `BACKUP_AND_DISASTER_RECOVERY.md` §7 | P |

## 5. Upload and media

| ID | Metric | Target | Current (configured, not measured) | Assumption | Phase |
|---|---|---|---|---|---|
| NFR-UP-01 | Max upload size, FD-V1 documents (script, research PDF, DOCX, images) | 100 MB | 100 MB (`storage_max_upload_bytes`) | Matches current config. Screenplays and research documents are far below this | A |
| NFR-UP-02 | Max upload size, FD-V2 media (footage, generated video, audio) | 10 GB per file through presigned multipart upload. Larger camera originals: **OPEN — DEC-003** (out-of-band transfer) | Not supported. Also, **`assets.size_bytes` is a 32-bit `Integer`** (`packages/persistence/models.py`), which overflows above 2,147,483,647 bytes | 10 GB covers a 1080p ProRes 422 proxy of several minutes or a long 4K H.264 take. Requires migrating `size_bytes` to `BigInteger` (additive: new column → backfill → switch) | FD-V2 |
| NFR-UP-03 | API process memory per in-flight upload | ≤ 16 MB (one streaming chunk), regardless of file size | **Whole file in memory.** `routers/assets.py:27` reads `max_bytes + 1`, and `store_stream` calls `stream.read()` | Streaming hash-while-write for small files; presigned direct-to-bucket for media (ADR-008) | A (stream) / P (presigned) |
| NFR-UP-04 | Validation before an asset becomes `available` | 100 % of uploads have a magic-byte signature check, an allowlist check, and (for C3/C4 classes, see Privacy doc) a malware scan | Client MIME trusted; no sniffing or scan (SEC-05) | Asset processing states `pending_scan → available / quarantined` (ADR-008) | P |
| NFR-UP-05 | Derivative availability (thumbnail, ffprobe metadata, proxy) after upload completes | Thumbnail ≤ 60 s p95 for images; video proxy ≤ 2 × clip duration p95 (FD-V2) | NOT APPLICABLE | Dedicated `media` worker pool. The proxy target assumes CPU transcoding of a 1080p H.264 proxy; re-derive once the pool is sized | FD-V2 |

## 6. Security

| ID | Requirement | Target | Current | Assumption / reference | Phase |
|---|---|---|---|---|---|
| NFR-SEC-01 | Authenticated routes | 100 % of routes except `/health` and `/ready` require a verified token | 0 %. `X-Actor-ID` header only (SEC-01) | ADR-003, DEC-002 | A (internal IdP) |
| NFR-SEC-02 | Fail-closed configuration | The process refuses to start if `ENVIRONMENT` is unset, or if `staging`/`production` would run with default DB credentials or the dev identity fallback | Defaults to `development`, so it is open (SEC-02) | `DEPLOYMENT_AND_DEVOPS.md` §8 | A |
| NFR-SEC-03 | Negative authZ coverage | Every route × every role in the matrix has a test asserting 403/404 for disallowed roles | No RBAC, no tests | `TESTING_AND_QA_STRATEGY.md` §5 | P |
| NFR-SEC-04 | Open findings at release | 0 Critical/High open. Medium findings need an owner and a date | 2 Critical, 3 High (`docs/audit/08`) | `SECURITY_THREAT_MODEL.md` §4 | P (Critical) / GA (High) |
| NFR-SEC-05 | Dependency vulnerabilities | Critical CVE in a runtime dependency patched or mitigated within 7 days; High within 30 days | No scanning | CI `pip-audit` + image scan (DevOps §4) | P |
| NFR-SEC-06 | Secret rotation | Provider and DB credentials rotatable without a redeploy of code; rotated at least every 90 days and immediately on suspicion | Env vars / `.env` only | Secret manager (DevOps §7) | GA |
| NFR-SEC-07 | Encryption | TLS 1.2+ on all external hops and to managed PG/object storage; at-rest encryption on DB, backups and buckets | Local, plaintext | Managed services' native encryption; SSE-KMS or equivalent for buckets holding C4 data | P |
| NFR-SEC-08 | Rate limiting | Per-actor limits on AI-triggering and upload routes (initial: 30 workflow starts/min/actor, 60 uploads/h/actor); 429 with `Retry-After` | None (SEC-10) | Initial values protect provider budgets and worker pools at the expected tier. Tune from `tattva_http_requests_total` once data exists | P |
| NFR-SEC-09 | Audit completeness | 100 % of canonical mutations, approvals, consent changes and external submissions emit an `audit_events` row in the same transaction. Audit is append-only for the app role | Committed slices emit audit rows; table mutable (SEC-07); manual POSTs partly bypass (SEC-06) | Audit coverage test per router (Testing §4) | P |

## 7. Accessibility and usability

| ID | Requirement | Target | Current | Assumption | Phase |
|---|---|---|---|---|---|
| NFR-A11Y-01 | Production workspace accessibility | WCAG 2.2 AA for every screen in the FD-V2 production workspace | NOT MEASURED | Depends on ADR-002 (frontend). A React/Next.js workspace can be held to AA with axe-core checks in Playwright | FD-V2 / GA |
| NFR-A11Y-02 | Streamlit alpha / control surface | Documented known gaps. Keyboard operation of all approval actions. No information conveyed by colour alone (approval/continuity status shows text + colour) | NOT MEASURED | Streamlit offers limited control over semantics (`docs/audit/04` §3), so AA is not promised for the alpha | A |
| NFR-UX-01 | Explicit states | Every screen implements loading / empty / error / recovery / awaiting-approval / mock-generator states | Partial (`components.safe_call` shows errors only) | `SCREEN_INVENTORY_AND_BEHAVIOUR.md` (Phase B, product) | A |
| NFR-UX-02 | Generator honesty | Every run and candidate carries a `generator_mode` (`deterministic` / `mock` / `live:<model>`), shown in the UI | Not shown (`docs/audit/04` §4.5) | OPEN_DECISIONS invariant 3, "no fake success" | A |

## 8. Data, correctness and maintainability

| ID | Requirement | Target | Current | Phase |
|---|---|---|---|---|
| NFR-DATA-01 | Version integrity | Unique `(project_id, version_number)`; every version bump takes a project row lock | No constraint; three services bump without a lock (PERF-06) | A |
| NFR-DATA-02 | Tenant isolation | 0 unscoped repository getters for tenant data; foreign IDs in bodies validated against caller's project | 3 unscoped getters, 2 unvalidated foreign IDs (SEC-04) | A |
| NFR-DATA-03 | Migration safety | Every migration passes `upgrade head → downgrade -1 → upgrade head` in CI. Backfills ship with a row-count reconciliation | Drift test only (`tests/integration/test_migrations.py`) | A |
| NFR-QA-01 | Test gate | 100 % of the suite passes on `main`; no test counted as passed unless executed | 47 pass / 5 fail / 1 error | A |
| NFR-QA-02 | Type gate | `mypy` runs in CI. Error count is non-increasing per PR until 0, then gated | 321 errors; plain `mypy` aborts | A (runnable) / P (0 errors in `packages/domain`, `packages/services`) |
| NFR-OBS-01 | Diagnosability | 100 % of API requests and worker tasks log `request_id` / `workflow_run_id`; traces cover API → outbox → worker → graph → provider | stdlib text logging only | A (logs) / P (traces) |

## 9. Cost

| ID | Requirement | Target | Current | Phase |
|---|---|---|---|---|
| NFR-COST-01 | Spend control | No paid external submission without an explicit approval that shows the estimated cost; per-project budget gate enforced server-side | No providers exist | FD-V2 (gate designed in FD-V1, `COST_AND_CAPACITY_MODEL.md` §4) |
| NFR-COST-02 | Usage attribution | 100 % of model and provider calls produce a `usage_records` row with org, project, run, provider, model and units | None | P (model calls) / FD-V2 (providers) |

## 10. Decisions referenced

- **OPEN — DEC-026 (new):** pilot support hours and availability tier. Recommendation: business-hours support with 99.5 % for the pilot; 99.9 % with on-call only at GA.
- **OPEN — DEC-004:** LLM latency targets after the eval spike.
- **OPEN — DEC-003:** file sizes above 10 GB.
- ADR-002 governs NFR-A11Y-01.
