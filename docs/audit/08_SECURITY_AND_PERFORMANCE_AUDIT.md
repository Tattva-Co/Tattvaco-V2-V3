# 08 — Security and Performance Audit

**Doc ID:** TFD-AUDIT-008 · **Audit date:** 2026-11-05 · Static review plus executed test suite. No penetration test or load test was performed.

## 1. Security findings (ranked)

| ID | Severity | Finding | Evidence | Required response |
|---|---|---|---|---|
| SEC-01 | **Critical** | Identity = unauthenticated `X-Actor-ID` header; any user UUID impersonates that user | `apps/api/dependencies.py::get_actor`, `services/identity.py::IdentityService.resolve` | Real authentication (OIDC/JWT via provider adapter, DEC-002); header identity only in `test` |
| SEC-02 | **Critical** | Dev fallback is enabled by default (`environment="development"` default) and may bind to an **arbitrary org** (`select(OrganizationModel).first()`) | `core/config.py:24`; `repositories.py:69-71` | Default `environment` must fail closed; fallback restricted to an explicit local flag and the `default-studio` org only |
| SEC-03 | High | No authorization: no roles, project membership, management authority or approval policy | `UserModel.role` never read | RBAC + project membership + capability matrix; server-side on every route |
| SEC-04 | High | Unscoped getters and unvalidated foreign IDs allow cross-tenant references | `ResearchRepository.get_question/get_source`, `FilmBibleRepository.get_rule`; `create_source(asset_id)`, `create_rule(historical_claim_id)` | Scope every getter; validate referenced IDs belong to the same project |
| SEC-05 | High | Upload: whole file in memory; client-trusted MIME; no signature sniffing, malware scan, quarantine or sandboxed parsing | `routers/assets.py:27`, `storage/service.py:142` | Streaming upload, magic-byte check, scan/quarantine states, parser isolation, decompression-bomb limits |
| SEC-06 | Medium | Manual research/film-bible POSTs write canonical data without approval or versioning | `ResearchService.create_*`, `FilmBibleService.create_rule` | Route through candidate→approval or a role-gated direct-canon path with audit + version |
| SEC-07 | Medium | Audit log is mutable by the app role | `audit_events` table, no grants/trigger | Append-only DB grants; optional hash chain |
| SEC-08 | Medium | Unknown approval scope falls through to script service | `routers/approvals.py` `else` branch | Explicit dispatch table; 422 on unknown scope |
| SEC-09 | Low (local) | Hardcoded local-dev DB credentials as defaults | `core/config.py:39` `database_url` default; `docker-compose.yml` `POSTGRES_PASSWORD` | Require `DATABASE_URL` in staging/prod (no default); secret manager |
| SEC-10 | Low | No rate limiting, request size limits beyond upload, or security headers | `main.py` | Gateway/LB rate limits; per-route limits for AI triggers |
| SEC-11 | Info | No prompt-injection controls, but no LLM exists yet | — | Required before ModelGateway goes live |
| SEC-12 | Info | No consent / likeness / voice authorization model | — | P0 before any digital-double or voice work (Master Prompt §6.5, §9) |

**Positive controls to preserve:**
- `org_id` is derived from the DB, not the request.
- Scoped repositories return 404 with no existence oracle.
- CORS uses an allowlist with no credentials and minimal methods and headers.
- Storage is content-addressed, write-once, with a path-traversal guard.
- The approval row is locked and committed before graph resume.
- No real secrets are tracked: a grep of tracked files for key and private-key patterns found none, and `.env` is not tracked.

## 2. Performance and scalability findings

| ID | Finding | Evidence | Impact | Response |
|---|---|---|---|---|
| PERF-01 | Workflows run inside HTTP requests by default | `schemas.py` `sync_execution: bool = True` (4 request models) | API worker starvation; timeouts once real LLMs are added | Async-by-default (202 + run id); sync only in tests |
| PERF-02 | Checkpointer `setup()` on every graph invocation | `workflows/checkpointer.py` | Extra DDL round-trips per run | Run once at deploy |
| PERF-03 | Uploads buffered in memory (100 MB cap) | `routers/assets.py:27` | Memory pressure; blocks video support | Streaming to object storage, presigned uploads |
| PERF-04 | Worker: single task per process, no lease, no retry | `apps/worker/worker.py` | Stuck tasks after crash; no throughput scaling knobs | Lease + heartbeat + retry/backoff + DLQ; concurrency setting; per-workload pools |
| PERF-05 | No pagination on list endpoints | all GET list routes | Unbounded responses as projects grow | Cursor pagination |
| PERF-06 | Version-bump race (correctness under concurrency) | `research_review.py:170`, `storyboard_review.py:151`, `film_bible_review.py:158` | Duplicate version numbers | `for_update` lock + unique constraint |
| PERF-07 | No metrics, tracing or slow-query logging | `core/logging.py` | Cannot measure anything | OpenTelemetry + structured logs + `pg_stat_statements` |

No load, stress or soak tests exist. **No performance figure can be claimed.** Capacity targets are set with documented assumptions in Phase B (`SCALABILITY_PERFORMANCE_CAPACITY_PLAN.md`, `NON_FUNCTIONAL_REQUIREMENTS.md`).

## 3. Resolution log

| ID | Resolved in | How |
|---|---|---|
| SEC-01 | C3 (`feat/c1-g04-fix-forward`, 2026-11-06) | `AuthProvider` port + Bearer-token verification outside `test`; see ADR-003 implementation note, DEC-002 in `11_APPROVAL_GATE_DECISIONS.md`. |
| SEC-02 | C3 | `get_or_create_default_actor()`'s `.first()`-org fallback removed entirely; replaced by `get_or_create_dev_user()`, which only ever resolves `default-studio`, called only from the explicit, dev-only `POST /auth/dev-login`. `environment` defaults to `development`, which now *requires* a valid token (fails closed with a 500 if `SECRET_KEY` is unset) rather than silently admitting any caller. |
| PERF-02 | C2 (2026-11-06) | Checkpoint `setup()` moved out of the per-invocation hot path into a process-start hook (`setup_checkpointer_schema()`, FastAPI lifespan / worker startup / test bootstrap). This also fixed a `CREATE INDEX CONCURRENTLY` deadlock against the caller's own idle transaction. |

SEC-03/04/08 (authorization, tenant-scoped getters, unknown-scope dispatch) remain open; scheduled for C4/C5.
