# 09 — Test and Quality Audit

**Doc ID:** TFD-AUDIT-009 · **Audit date:** 2026-11-05

## 1. How tests run
- The DB is real PostgreSQL from `docker-compose.yml` (`:55432`). The schema must be at Alembic head. There is no SQLite and no testcontainers.
- Command: `docker compose up -d && .venv/bin/alembic upgrade head && .venv/bin/python -m pytest`
- Config: `pyproject.toml`, `testpaths=["tests"]`, `asyncio_mode=auto`.
- Fixtures: `tests/conftest.py` provides `TestClient(app)`, `tenant` and `other_tenant`. `tests/support.py::purge_organization` deletes tenant rows on teardown.
- **Tests share the developer's dev database.** There is no isolated test DB.

## 2. Executed result (2026-11-05, `pytest -p no:cacheprovider`)
**47 passed, 5 failed, 1 error in 6.78 s.** All 6 non-passing results are G-04 WIP:
- 5 fail on `AttributeError: list_claims_for_project` (defect G04-B).
- 1 errors in teardown on `ForeignKeyViolation film_bible_rules_project_id_fkey` (defect G04-C).

**Side effect:** each run currently leaves orphan test-tenant rows in the dev DB until G04-C is fixed.

Other quality gates:
- `ruff check .` passes.
- `mypy --explicit-package-bases packages apps` reports **321 errors in 31 files**. Plain `mypy` aborts on module resolution, so **typing is not an enforced gate.**
- There is no CI, so none of these run automatically.

## 3. Test inventory

| File | Covers | Result |
|---|---|---|
| `tests/api/test_assets_api.py` | Upload MIME, size and empty-file checks; non-text refused | pass |
| `tests/api/test_script_intelligence_slice.py` | G-01 end to end, partial selection, rejection | pass |
| `tests/api/test_historical_research_api.py` | Questions/sources CRUD, G-02 end to end, rejection | pass |
| `tests/api/test_storyboard_api.py` | G-03 end to end, partial approval, rejection | pass |
| `tests/api/test_film_bible_api.py` (WIP) | Rules CRUD, G-04 end to end, conflicts, partial approval, rejection | **4 fail, 1 error** |
| `tests/api/test_tenant_isolation_api.py` | Cross-org access denied | pass |
| `tests/integration/test_migrations.py` | Model ↔ migrated schema drift | pass |
| `tests/integration/test_storage_service.py` | Immutability, path traversal | pass |
| `tests/unit/test_invariants.py` | Scope and version invariants | pass |
| `tests/unit/test_ui_smoke.py` | Each Streamlit view renders against a fake API | pass |
| `tests/workflows/test_graph_recovery.py` | G-01 checkpoint/interrupt/resume across a new checkpointer; rejection | pass |
| `tests/workflows/test_worker.py` | Outbox drain per graph; failure path | 1 fail (film bible) |

## 4. Coverage gaps against Master Prompt §23

| Required test type | Present? |
|---|---|
| Unit / API / integration / DB / migration | Partial (migration upgrade/downgrade not tested; drift only) |
| Workflow + crash recovery | G-01 only; no worker-crash or redelivery test |
| Tenant isolation | Org-level for projects; **not** for research/film-bible getters or foreign-ID references |
| Authorization (roles) | None (no RBAC exists) |
| Provider adapter / contract | None (no adapters) |
| Manual import/export | None |
| Media handling (large, malicious, signature mismatch) | None |
| AI evaluation (golden sets) | None |
| UI E2E (browser) | None (smoke render only) |
| Concurrency (version race) | None |
| Load / stress / soak | None |
| Security (authn bypass, IDOR) | None beyond org isolation |
| Backup & restore | None |

## 5. Immediate quality actions (Phase C, pending approval)
1. Fix G04-A/B/C and add a regression test for each. This is approval gate #3.
2. Use a dedicated test database (`tattva_test`) created per session and migrated to head, so test runs never pollute dev data.
3. Add CI: ruff, pytest against a Postgres service, `alembic upgrade head` + `downgrade -1` + `upgrade` round-trip.
4. Make mypy runnable (`explicit_package_bases`, `mypy_path`). Burn down the errors by package, then gate.
5. Add a negative authorization matrix test per router family as soon as RBAC lands.
