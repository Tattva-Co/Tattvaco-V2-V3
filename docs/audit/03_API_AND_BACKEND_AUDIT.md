# 03 — API and Backend Audit

**Doc ID:** TFD-AUDIT-003 · **Audit date:** 2026-11-05 · **Baseline:** `main@b3621cb` + G-04 WIP

## 1. Application shell
- `apps/api/main.py::create_app`:
  - `/health` is mounted at the root; all routers are under `/api/v1`.
  - CORS: `allow_origins=settings.cors_allow_origins` (default `["http://localhost:8501"]`), `allow_credentials=False`, methods `GET, POST`, headers `Content-Type, X-Actor-ID`. **The Gap Report finding "wildcard CORS" is fixed.**
- `apps/api/errors.py` maps domain errors to `{"detail","error"}`: 401 auth, 403 tenant, 404 not found, 409 version/state, 413 size, 415 type, 422 validation. Anything else becomes a logged 500.
- Layering is good. Routers → `packages/services/*` → `packages/persistence/repositories.py`. Domain errors and invariants are in `packages/domain/`.

## 2. Route inventory

| Router | Method & path (under `/api/v1`) | Service | Notes |
|---|---|---|---|
| health | GET `/health` (root) | inline `SELECT 1` | Liveness only, no readiness |
| projects | POST `/projects` (201), GET `/projects`, GET `/projects/{id}` | `ProjectService` | Scoped via `get_scoped(org_id)` |
| projects | GET `/projects/{id}/versions`, `/audit-log`, `/candidates`, `/scenes`, `/entities` | `ProjectService`, repos | Read only |
| assets | POST `/projects/{pid}/assets/upload`, GET `/projects/{pid}/assets` | `AssetService` | See §5 |
| workflows | POST `/projects/{pid}/workflows/{script-intelligence\|historical-research\|storyboard-intelligence\|film-bible-synthesis}` | per-graph `*Service.start` | `sync_execution: bool = True` default (`schemas.py:90,240,270,345`) |
| workflows | GET `/workflow-runs/{run_id}` | `WorkflowRunRepository.get_scoped` | Polling endpoint exists, but the UI does not use it |
| approvals | POST `/approvals/{id}/decide` | dispatch by `approval.scope` | **The `else` branch sends any unknown scope to `ScriptIntelligenceService`** |
| research | GET/POST `/projects/{pid}/research/questions`, `/sources`; GET `/claims`, `/conflicts` | `ResearchService` | Manual POSTs write canonical rows directly |
| storyboard | GET `/projects/{pid}/storyboard/panels` | repo | — |
| film_bible (WIP) | GET/POST `/projects/{pid}/film-bible/rules` | `FilmBibleService` | POST bypasses approval (G04-D) |

There are no PUT, PATCH or DELETE routes, no pagination on list routes, and no API versioning policy beyond the `/api/v1` prefix.

## 3. Authentication (P0 blocker)

`apps/api/dependencies.py::get_actor` → `services/identity.py::IdentityService.resolve`:
- The identity is the `X-Actor-ID` header naming any existing user UUID. **Possession of a user UUID equals full impersonation.** There is no token, session or signature, and `SECRET_KEY` in `.env.example` is unused.
- If the header is missing and `settings.environment ∈ {development, test}`, the dev fallback runs `UserRepository.get_or_create_default_actor()`.
  - `packages/core/config.py:24` sets the default `environment` to `"development"`. **A deployment that forgets to set `ENVIRONMENT` is unauthenticated.**
  - The fallback org is `slug == "default-studio"` **or `select(OrganizationModel).first()`**, which can be any tenant (`repositories.py:69-71`).
- Positive: `org_id` is always derived from the DB user, never from the request.

## 4. Authorization (P0 blocker)
- **No role or capability checks exist.** `UserModel.role` is stored and never read.
- Any org member can approve or reject any workflow, create research sources or film-bible rules, and upload assets.
- There is no project membership; org membership implies access to every project.
- No management-authority concept exists, which the locked-screenplay requirement needs.

## 5. Tenant isolation

**Good:**
- `ProjectRepository.get_scoped`, `ApprovalRepository.get_scoped` and `WorkflowRunRepository.get_scoped` filter by org and raise `NotFoundError`, so there is no existence oracle.
- `tests/api/test_tenant_isolation_api.py` passes.

**Gaps:**
1. `ResearchRepository.get_question/get_source` and `FilmBibleRepository.get_rule` are unscoped.
2. Foreign IDs in request bodies are not validated against the caller's project/org: `create_source(asset_id=…)`, `create_rule(historical_claim_id=…)`. A row can therefore reference another tenant's data.
3. `scenes`, `entities`, `scene_candidates`, `entity_candidates` and `project_versions` have no `organization_id`. Isolation depends on always joining through `projects` first.
4. `domain/invariants.assert_project_scope` exists but is not used on these paths.

## 6. Upload handling
- `routers/assets.py:27` reads `await file.read(max_bytes + 1)`, so the whole file is in memory. `LocalFileSystemStorageService.store_stream` (`storage/service.py:142`) also calls `stream.read()`.
- The size cap (`storage_max_upload_bytes`, 100 MB) is enforced in the router and in `AssetService.validate_upload`, and empty files are rejected.
- MIME validation trusts the client `Content-Type` and falls back to the extension. **There is no magic-byte sniffing, no malware scan and no quarantine.**
- The allowlist is text/plain, PDF, DOCX and JSON, **but PDF and DOCX are decoded as UTF-8 with `errors="replace"`** in `script_review.py`, so non-text formats feed garbage to the parser.
- Storage is content-addressed (`{org}/{project}/{sha256}_{safe_name}`), write-once, with a path-traversal guard. This is good and should be kept.

## 7. Transactions, concurrency, idempotency

| Concern | Finding |
|---|---|
| Approval decision | Locks the approval row (`for_update=True`) and commits the decision **before** resuming the graph. This is correct and matches ADR-001 invariant 4. |
| Project version bump | `script_review.py:206` locks the project row. **`research_review.py:170`, `storyboard_review.py:151` and `film_bible_review.py:158` read `current_version` and increment it without a lock.** Combined with no unique `(project_id, version_number)` constraint, concurrent approvals can create duplicate version numbers. |
| Idempotency | None. Every POST creates new rows, and there is no `Idempotency-Key`. Asset bytes are deduplicated by path, but asset rows are not. |
| Long work in requests | `sync_execution=True` runs LangGraph inside the HTTP request. `PostgresSaver.setup()` runs on every invocation (`workflows/checkpointer.py`). |
| Error mapping | Consistent domain→HTTP mapping. No problem-details (RFC 9457) format and no correlation ID in responses. |

## 8. Worker (`apps/worker/worker.py`)
- `process_one_task` → `OutboxRepository.claim_next` (`repositories.py:191`): `FOR UPDATE SKIP LOCKED` on the oldest PENDING task, then CLAIMED and `attempts += 1`. It is safe to run several worker processes.
- **On any exception, the task goes to FAILED permanently.** There is no retry, backoff, max-attempts check, dead-letter queue or cancel.
- **A CLAIMED task whose worker crashed is never reclaimed.** No lease or heartbeat exists, and nothing sweeps by `claimed_at`.
- `*Service.execute()` invokes the graph with a fresh initial state on the same thread, so a re-execution restarts from START instead of resuming the checkpoint. That can duplicate candidates.
- Each process handles one task at a time. There is no workload-specific pool.

## 9. Configuration & secrets
- `packages/core/config.py` (pydantic-settings) is the single place configuration is read.
- Unused keys: OpenAI, Anthropic, Gemini and Higgsfield API keys, `SECRET_KEY`, `CHECKPOINT_SCHEMA` and `WORKER_CONCURRENCY` are declared or in `.env.example` but never read.
- No secrets are committed (verified by grep of the tracked tree for key patterns). There is no secret-manager integration.

## 10. Backend verdict

| Keep | Change (P0) | Avoid |
|---|---|---|
| Service/repository layering, domain errors, scoped repos, approval-before-resume, content-addressed storage, outbox | Real authentication; RBAC and project membership; scope every repo getter; lock the project row on every version bump plus a unique constraint; async-by-default; worker lease, retry and dead-letter; idempotency keys; streaming upload plus signature sniffing | Microservices, a separate queue broker before measured need, rewriting the slice services |
