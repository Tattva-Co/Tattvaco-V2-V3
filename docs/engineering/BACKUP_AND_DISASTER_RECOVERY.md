# Backup and Disaster Recovery

**Doc ID:** TFD-ENG-007 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval
**Inputs:** `docs/audit/05` §4 (data-protection rules), `08` · `packages/persistence/models.py` (`AssetModel`, `WorkflowRunModel`) · `packages/storage/service.py` · `packages/workflows/checkpointer.py` · `packages/core/config.py` (`checkpoint_database_url`) · NFR-DR-01..03, NFR-DUR-01..03 · DEC-001, DEC-003, DEC-007

---

## 0. Current state

- **No backups of any kind.** The DB lives in the Docker volume `tattva_pgdata`. Assets live on the local filesystem at `data/storage/` (gitignored; about 130 residual test files).
- LangGraph checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) are in the **same database** as the canonical tables, because `checkpoint_database_url` is unset. They are excluded from Alembic autogenerate by `migration_filters.include_object`.
- Storage keys are content-addressed: `{org}/{project}/{sha256}_{safe_name}`. They are write-once (`store_bytes` skips the write if the path exists). Two `assets` rows may point to the same key (byte dedup, not row dedup; `docs/audit/03` §7).

## 1. What must be recoverable

| Data | Location | Criticality | Recovery means |
|---|---|---|---|
| Canonical tables (projects, versions, scenes, entities, research, storyboard, film bible, approvals, audit, all future governance and consent tables) | Postgres | Highest: system of record | PITR |
| `performer_consents` and consent documents | Postgres + object storage (C4) | Highest, with legal weight | PITR + versioned objects; restore must never resurrect revoked consent (§6.3) |
| LangGraph checkpoints | Postgres (same DB, or separate via `checkpoint_database_url`) | Medium: needed only for runs in flight or paused at `interrupt()` | PITR alongside canonical; a lost checkpoint is recovered by restarting the run (§5) |
| `outbox_tasks` | Postgres | Medium: rebuilt from `workflow_runs` state | PITR |
| Original assets | Object storage | Highest: originals are irreplaceable | Versioning + object lock + cross-region replication (GA) |
| Derivatives (thumbnails, proxies, waveforms) | Object storage | Low: regenerable from originals | Regenerate |
| Logs and traces | Observability backend | Low | Not backed up beyond retention |
| Secrets | Secret manager | High | Provider-managed versioning; documented re-issue procedure |

## 2. PostgreSQL: point-in-time recovery

- Managed PG16 (DEC-001) with **automated daily base backups and continuous WAL archiving**. Retention 14 days at pilot and 35 days at GA (assumption: covers a two-sprint detection window for logical corruption).
- RPO is governed by WAL archive frequency. Target ≤ 15 min at pilot and ≤ 5 min at GA (NFR-DR-01). Choose a managed tier whose archive interval meets this; record it as evidence.
- An **on-demand snapshot** is taken before every production migration (DevOps §5) and kept for 30 days.
- **Logical exports:** weekly `pg_dump --format=custom` of the canonical schema (excluding `checkpoint*`) to a separate backup bucket in a separate account or project with a restore-only role. Encrypted with a KMS key that is distinct from the primary data key. This protects against provider-level loss and accidental instance deletion.
- Backup security (Master Prompt §21): backups are encrypted; access is limited to a `backup-restore` role with MFA; every access is logged; backup buckets use object lock (compliance mode) for the retention window.

## 3. Object storage: versioning and protection

- S3-compatible bucket(s) (ADR-008, DEC-003), with **versioning enabled** on every bucket.
- **Originals prefix** `orig/`: object lock in governance mode for active projects. Deletion requires the purge workflow (Privacy doc §4), which lifts governance retention under an audited privileged role.
- **C4 prefix** `c4/` (face references, body scans, voice): separate KMS key; access logging on.
- **Derivatives prefix** `deriv/`: versioning on; lifecycle expires non-current versions after 7 days.
- **Quarantine prefix** `quarantine/`: never served; expires after 30 days.
- Cross-region replication of `orig/` and `c4/` at GA (pilot: single region with provider durability). **OPEN — DEC-007** governs whether C4 data may leave its region at all.
- Migration from local FS: a one-time copy job uploads `data/storage/**` to `orig/`. It verifies `sha256(object) == assets.checksum_sha256` for every row and writes a manifest. Local files are kept until verification reaches 100 %.

## 4. Consistency between DB rows and asset bytes

**Invariant:** for every `assets` row whose state is `available`, an object exists at `storage_path` and its SHA-256 equals `checksum_sha256`. Every object under `orig/` is referenced by at least one row, or is younger than the upload grace period (24 h, covering `pending_upload` states).

### 4.1 Write ordering (prevents most drift)
1. Upload object → compute SHA-256 while writing (streaming) → `put` succeeds.
2. Insert the `assets` row in the same transaction as the audit event and any linkage.
3. If step 2 fails, the object is an orphan and is cleaned up by reconciliation (it is never served).
4. Presigned uploads (FD-V2): the row exists first in state `pending_upload`; `complete` verifies size and checksum (S3 checksum header or a server-side re-hash by the media worker) before setting `available`.

### 4.2 Reconciliation job (maintenance pool, daily)
| Check | Query / method | Outcome |
|---|---|---|
| Missing object | For each `assets` row in `available`: `HEAD storage_path` | `tattva_storage_reconciliation_drift{kind="missing_object"}`; asset set to `unavailable`; SEV-2 |
| Checksum mismatch | Sample 1 % of rows daily and 100 % monthly: stream the object and re-hash | `checksum_mismatch`; asset `quarantined`; SEV-1 (integrity) |
| Orphan object | List `orig/` (S3 inventory report when available) minus `SELECT DISTINCT storage_path FROM assets` | Older than 24 h → tagged `orphan`, deleted after 30 days unless claimed |
| Size check | `assets.size_bytes` vs object `ContentLength` | mismatch → `checksum_mismatch` path |

Output: a JSON report written to `ops/reports/reconciliation/<date>.json` in the backup bucket, plus metrics. The report is the evidence for the restore drill.

## 5. Checkpoint tables

| Topic | Design |
|---|---|
| Role | Recovery state for runs that are `running` or `awaiting_approval`. **Not** a system of record: canonical results live in canonical tables, and run status lives in `workflow_runs` |
| Backup | Covered by the same PITR as canonical tables (same instance). If `checkpoint_database_url` points to a separate instance, it **must** be restored to the same point in time as the canonical DB, otherwise a resume can replay a decision that canonical state has already absorbed |
| Consistency guard on resume | A resume compares `workflow_runs.status` and the approval row with the checkpoint's `approval_status`. G-01..G-03 already guard on `approval_status != "pending"`. G-04 lacks the guard (G04-G) and must get it before any restore relies on it. A run whose canonical commit already exists (`project_versions` row references the run) is marked `completed`, and its checkpoint is not resumed |
| Pruning | Delete checkpoint rows for threads whose run reached `completed`/`rejected`/`failed`/`cancelled` more than 30 days ago (runbook procedure). Pruning never touches threads in `awaiting_approval` |
| Loss scenario | If the checkpoint for a paused run is lost but the run and approval exist: mark the approval `expired`, mark the run `failed` with reason `checkpoint_lost`, and the user re-runs. Candidates stay as history. No canonical data is lost |

## 6. RPO / RTO

| Scenario | RPO | RTO | Procedure |
|---|---|---|---|
| Single DB node failure | 0 (managed HA standby) | ≤ 5 min (automatic failover) | Provider failover; API/worker reconnect via `pool_pre_ping=True` (already set) |
| Logical corruption (bad migration or bad backfill) | Time of the pre-deploy snapshot or the chosen PITR point | ≤ 4 h pilot / ≤ 1 h GA | §7 restore → reconcile → re-apply legitimate writes from audit events after the restore point (manual, audited) |
| Accidental delete of objects | 0 (versioning) | ≤ 1 h | Restore the prior version; reconciliation confirms |
| Region loss | Pilot: last logical export (≤ 7 days) + WAL if replicated. GA: ≤ 15 min via cross-region replica | Pilot: 24 h. GA: 4 h | Promote the replica / restore in a secondary region; DNS switch |
| Ransomware / credential compromise | Last immutable backup | ≤ 24 h | Restore from object-locked backups into a clean account; rotate every secret (Incident runbook) |

### 6.3 Restoring around consent revocations
A PITR to a time **before** a consent revocation would bring the consent back to life. After any restore, the restore procedure replays **revocations** recorded after the restore point. Sources: the `audit_events` export in the backup bucket (written daily) and the Legal-held consent register. No C4-dependent job may run until this replay is done (`FF_PROVIDER_*` off and the consent gate in strict mode during restore).

## 7. Restore drill procedure

Frequency: once before closed pilot, then quarterly, and after any change to backup configuration. Owner: platform engineer on rotation; observer: product or security.

1. **Declare** the drill in the ops channel; choose a target time T (for example 2 h ago).
2. **Provision** an isolated restore environment from IaC (no production network peering, no real IdP, no provider credentials).
3. **Restore** Postgres to T via PITR into a new instance. Record the wall-clock start and end.
4. **Point** the storage adapter at the production bucket **read-only** (a role restricted to `GetObject` and object versions as of T).
5. **Schema check:** `alembic current` equals the expected head for T; `/ready` passes.
6. **Reconcile:** run §4.2 at 100 % checksum mode for one sampled project and existence mode for all. Expect 0 `missing_object`.
7. **Consent replay check:** confirm that the revocation replay (§6.3) step runs and is idempotent.
8. **Smoke:** log in with a drill account; open a project; list scenes, versions and audit log; resume a run that was `awaiting_approval` at T with a decision in the drill env; confirm canonical commit and version bump.
9. **Measure:** RPO = T minus the newest committed transaction found; RTO = time from step 3 start to step 8 pass. Compare with NFR-DR-01.
10. **Record** evidence: timestamps, reconciliation report, smoke JUnit output, deviations. File it as `ops/drills/<date>-restore.md`, link it in the Release Readiness Checklist, and open issues for every deviation.
11. **Tear down** the environment; confirm deletion of the restored data (it contains production C3/C4 data).

## 8. Open decisions

- **OPEN — DEC-001:** managed PG tier must meet the PITR interval in §2.
- **OPEN — DEC-003:** object storage must support versioning, object lock and server-side checksums. MinIO (self-hosted), S3 and R2 differ on object-lock support, so verify before choosing.
- **OPEN — DEC-007:** retention windows for backups that contain C4 data. Deleting a performer's data cannot reach into immutable backups until they expire, so the backup retention must be disclosed in the consent terms.
