# 05 — Database and Migration Audit

**Doc ID:** TFD-AUDIT-005 · **Audit date:** 2026-11-05

## 1. Migration chain (linear, verified)

| # | Revision | down_revision | Adds | Committed |
|---|---|---|---|---|
| 1 | `e16ffe799e44` | None | 13 core tables: organizations, users, projects, project_versions, assets, workflow_runs, outbox_tasks, approval_requests, audit_events, scene_candidates, entity_candidates, scenes, entities | Yes |
| 2 | `0d204c88a75f` | `e16ffe799e44` | research_questions, research_sources, research_claims, research_conflicts, research_claim_candidates, research_question_candidates | Yes (G-02) |
| 3 | `066e52ac4889` | `0d204c88a75f` | storyboard_panels, storyboard_panel_candidates | Yes (G-03) |
| 4 | `00b7cd57e036` | `066e52ac4889` | film_bible_rule_candidates, film_bible_rules (+ indexes) | **No (WIP), already applied to the local DB** |

- `alembic current` = `alembic heads` = `00b7cd57e036` (executed 2026-11-05).
- `migration_filters.include_object` excludes LangGraph `checkpoint*` tables from autogenerate. This is correct.
- `tests/integration/test_migrations.py` (schema-drift check) **passes** against the WIP head.
- Risk: if the WIP is ever discarded, the local DB carries a revision with no file. You would need `alembic downgrade 066e52ac4889` **before** removing the file.

## 2. Schema observations (`packages/persistence/models.py`)

| Observation | Impact | Recommendation |
|---|---|---|
| IDs are `String(36)` UUIDs; no `relationship()`, FKs only | Fine; explicit queries | Keep |
| **All status and enum columns are plain strings**; no CHECK constraints | Invalid states can be written (e.g. film-bible `category` / `strictness` unvalidated) | Add CHECK constraints or validation in services; do not use PG ENUM types (migration friction) |
| `project_versions`: **no unique `(project_id, version_number)`**, no `organization_id` | Duplicate versions possible under the race in `03` §7 | Add unique constraint (after dedupe check) and `org_id` |
| `scenes`, `entities`, `*_candidates`: no `organization_id` | Isolation depends on joins | Add `organization_id` (additive, backfill from `projects`) |
| FKs have **no `ondelete` policy** | Project deletion impossible; test teardown fragile (G04-C) | Define retention/deletion policy first (DEC-007), then cascades or soft-delete |
| **`assets.size_bytes` is a 32-bit `Integer`** (`models.py:85`) | Uploads of 2.1 GB or more overflow, which blocks FD-V2 footage | Migrate to `BigInteger` (additive alter; Postgres widens in place) |
| **`outbox_tasks.workflow_run_id` is `unique=True`** (`models.py:119`) | Only one task per run, so the column cannot hold retries or multi-stage dispatch | Relax via expand/contract (ADR-007) |
| `snapshot_data` JSON on project_versions | Opaque history | Add typed artifact/version references (Phase B DB design) |
| `assets` has `parent_asset_id`, `is_original`, `metadata` JSON | Good lineage start | Extend with processing state, rights, retention, storage adapter, kind |
| `audit_events` is updatable by the app role | Not tamper-evident | Append-only grants or trigger; hash chain optional |
| No indexes reviewed beyond PKs/FKs and the new film-bible indexes | List queries unbounded | Index `(project_id, created_at)` on hot lists; add pagination |

## 3. Concepts the target model needs vs present

| Target group (Master Prompt §19) | Present today | Classification |
|---|---|---|
| organizations, users | `organizations`, `users` (role column unused) | Extend: memberships, project_memberships, roles |
| projects, project_versions | Yes | Extend: production format, production mode, delivery profile, template |
| screenplay_versions, screenplay_changes, management_approvals, creative_decisions | No | New |
| scenes | Yes (canonical, from G-01) | Extend: screenplay_version_id, production_mode |
| sequences, shots, dialogue_segments | No (`storyboard_panels.shot_type` only) | New |
| storyboards, storyboard_panels | `storyboard_panels` | Extend: frame asset mapping, scene/shot mapping |
| research_sources, evidence_claims, conflicts | `research_*` | Extend: evidence locators, timeline_events (new) |
| characters & digital human group (15 tables) | `entities(category=character)` only | New, with entities as legacy adapter |
| costume/prop/environment group | No | New |
| cinematography & on-set group | No | New (JSONB for extensible camera params) |
| assets & continuity group | `assets` only | Extend assets; new derivatives, provenance, continuity_* |
| provider & generation group | No | New (V2) |
| workflow_runs, approval_requests, outbox_tasks, audit_events | Yes | Extend: lease/retry fields, generalized approval scopes |
| film_bible_rules (WIP) | Yes (WIP) | Keep after G-04 fix; generalize into visual-language profile |

Full target schema, ERD and additive migration map: `docs/architecture/DATABASE_DESIGN_AND_ERD.md` (Phase B).

## 4. Data-protection rules for all future migrations
1. **Additive first:** expand → backfill → dual-read/verify → switch → contract (Gap Report §11).
2. Never drop or rename tables or columns in the same release as the new writer.
3. Never edit or delete an applied revision; fix forward.
4. Every migration ships with an upgrade/downgrade test and a row-count reconciliation for backfills.
5. Back up (pg_dump) before applying to any shared environment.
