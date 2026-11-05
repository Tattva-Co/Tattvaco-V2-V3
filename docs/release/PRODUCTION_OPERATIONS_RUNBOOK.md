# Production Operations Runbook

**Doc ID:** TFD-REL-003 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval
**Inputs:** `apps/worker/worker.py` · `packages/persistence/repositories.py::OutboxRepository.claim_next` · `packages/persistence/models.py` (`OutboxTaskModel`, `WorkflowRunModel`, `AssetModel`, `ApprovalRequestModel`) · `packages/domain/enums.py` (`WorkflowStatus`, `OutboxStatus`, `ApprovalStatus`) · `packages/workflows/checkpointer.py` · Alembic chain `e16ffe799e44 → 0d204c88a75f → 066e52ac4889 → 00b7cd57e036` · ADR-005, ADR-007, ADR-008 · `BACKUP_AND_DISASTER_RECOVERY.md`

---

## 0. Conventions

- **Two variants per procedure where it matters.** `CURRENT` applies to the code as it is today, without leases. `TARGET` applies after ADR-007 / ADR-008 land.
- **SQL** runs as the `readonly` role for inspection. Any write runs as an operator role inside an explicit transaction, and every write is recorded as an `audit_events` row or an ops ticket with the exact statement.
- **Status values** in code:
  - `workflow_runs.status`: `queued | running | awaiting_approval | completed | rejected | failed`; the model default is `pending`.
  - `outbox_tasks.status`: `pending | claimed | completed | failed`; target adds `dead_lettered`.
  - `approval_requests.status`: `pending | decided`.
- **Checkpoint tables** (LangGraph `PostgresSaver`): `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, keyed by `thread_id` = `workflow_runs.id`.

## 1. Worker: stuck tasks

**Symptoms:**
- Alert `tattva_outbox_oldest_pending_age_seconds` > 600.
- Stuck-claims SQL alert fires.
- A user reports "run stays queued/running".

### 1.1 Diagnose
```sql
-- Claimed but not progressing (CURRENT: no lease; anything > 30 min is suspect)
SELECT t.id AS task_id, t.task_type, t.status, t.attempts, t.claimed_by, t.claimed_at,
       r.id AS run_id, r.status AS run_status, r.updated_at, r.error_message
FROM outbox_tasks t JOIN workflow_runs r ON r.id = t.workflow_run_id
WHERE t.status = 'claimed' AND t.claimed_at < now() - interval '30 minutes'
ORDER BY t.claimed_at;

-- Pending backlog
SELECT task_type, count(*), min(created_at) FROM outbox_tasks WHERE status = 'pending' GROUP BY 1;

-- Does a checkpoint exist for the run? Is it paused at approval?
SELECT count(*) FROM checkpoints WHERE thread_id = :run_id;
SELECT id, status, scope FROM approval_requests WHERE workflow_run_id = :run_id;
```
Also check that worker processes are alive (platform console), look for `Claimed task <id>` without a matching `Completed task <id>` in the logs, and check for DB connection errors.

### 1.2 Decide

| Finding | Action |
|---|---|
| Pending backlog, workers alive but busy | Scale the worker replicas for the pool. Check for one slow task type |
| Pending backlog, no workers | Restart or scale workers from 0 |
| Claimed task; worker process gone; run `awaiting_approval` with a pending approval | **Do not requeue.** The graph reached `interrupt()`. Mark the task `completed` (the work up to the interrupt is done); the approval drives the rest |
| Claimed task; worker gone; run `queued`/`running`; **no checkpoint** | Requeue (§1.3) |
| Claimed task; worker gone; run `running`; **checkpoint exists** | CURRENT: requeueing **restarts the graph from START** and duplicates candidates (`docs/audit/06` §3). Instead: set run `failed` with reason `worker_crash_manual_restart`, mark the task `failed`, ask the user to re-run, and record that orphan candidates from the partial run exist. TARGET: requeue; the handler resumes from the checkpoint |
| Run already `completed`/`rejected` but task `claimed` | Mark the task `completed` |

### 1.3 Requeue (CURRENT)
```sql
BEGIN;
UPDATE outbox_tasks
   SET status = 'pending', claimed_by = NULL, claimed_at = NULL, updated_at = now()
 WHERE id = :task_id AND status = 'claimed';      -- expect 1 row
UPDATE workflow_runs SET status = 'queued', updated_at = now()
 WHERE id = :run_id AND status IN ('queued','running');
COMMIT;
```
The next poll claims the task (`attempts` increments). Watch the logs for `Completed task`.

### 1.4 TARGET (ADR-007)
- Leases expire on their own and the sweep reclaims them. No manual requeue is needed.
- Dead-lettered tasks are re-driven with `python -m apps.worker.admin redrive --task <id> --reason "<ticket>"`, which writes an audit event. Re-drive only after the root cause is fixed. Re-driving a poison task returns it to the DLQ after `max_attempts`.

### 1.5 Before deploying workers (CURRENT)
Scale workers to 0, wait until `SELECT count(*) FROM outbox_tasks WHERE status='claimed'` = 0, then deploy. Otherwise a kill mid-task leaves a stuck claim.

## 2. Migrations: apply and roll back

### 2.1 Pre-flight
1. Confirm the image's head: `alembic heads` returns one revision (today `00b7cd57e036`, which is **uncommitted WIP**; shared environments must not be created until DEC-010 commits it).
2. Confirm the target DB position: `alembic current`.
3. Check that CI passed the migration round trip for this SHA.
4. Take a snapshot (prod: managed snapshot; others: `pg_dump -Fc -d $DATABASE_URL -f pre_<rev>.dump`).
5. Read the migration's `MIGRATION_PHASE`. `contract` migrations require the `contract-migration` label and 2 approvals (DevOps §5).

### 2.2 Apply
Run the `migrate` job (`alembic upgrade head` as `migrator`, then the one-time checkpointer `setup()`). Watch for lock waits:
```sql
SELECT pid, state, wait_event_type, now() - query_start AS age, left(query, 120)
FROM pg_stat_activity WHERE datname = current_database() AND state <> 'idle' ORDER BY age DESC;
```
If an `ALTER TABLE` waits on a lock for more than 60 s, cancel the job. Migrations set `lock_timeout = '5s'` and retry. Then find the blocking long transaction.

Post-check: `alembic current` = head; `/ready` passes on new pods; run the backfill reconciliation query in the migration docstring and expect 0 mismatches.

### 2.3 Roll back
| Case | Procedure |
|---|---|
| Expand migration, app misbehaves | Roll back the **app image** only. Leave the schema (old code ignores new columns) |
| Expand migration failed midway | The transaction rolled back (transactional DDL). Fix forward with a new revision. **Never edit an applied revision** |
| `CREATE INDEX CONCURRENTLY` failed | Drop the `INVALID` index (`SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid`), then re-run |
| Must undo an expand in dev/staging | `alembic downgrade -1` as `migrator` after a snapshot |
| Contract migration lost data | PITR restore to the pre-migration snapshot in a new instance, reconcile, switch (Backup doc §6) |
| Local dev: discard the G-04 WIP | `alembic downgrade 066e52ac4889` **before** removing the `00b7cd57e036` file (`docs/audit/05` §1) |

## 3. Checkpoint pruning

**Why:** checkpoints are the largest DB growth term (capacity plan §6, row 14) and today they are never pruned.

**Rule:** delete checkpoint data for runs in a terminal state for more than 30 days. **Never** prune `awaiting_approval`, `queued` or `running`.

```sql
-- Dry run
SELECT count(*) AS runs FROM workflow_runs
WHERE status IN ('completed','rejected','failed') AND updated_at < now() - interval '30 days';

-- Batched delete (repeat until 0 rows; maintenance window not required)
BEGIN;
CREATE TEMP TABLE prune_threads ON COMMIT DROP AS
  SELECT id::text AS thread_id FROM workflow_runs
  WHERE status IN ('completed','rejected','failed') AND updated_at < now() - interval '30 days'
  AND EXISTS (SELECT 1 FROM checkpoints c WHERE c.thread_id = workflow_runs.id::text)
  LIMIT 500;
DELETE FROM checkpoint_writes WHERE thread_id IN (SELECT thread_id FROM prune_threads);
DELETE FROM checkpoint_blobs  WHERE thread_id IN (SELECT thread_id FROM prune_threads);
DELETE FROM checkpoints       WHERE thread_id IN (SELECT thread_id FROM prune_threads);
COMMIT;
```
Afterwards: `VACUUM (ANALYZE) checkpoints, checkpoint_blobs, checkpoint_writes;`. Record row counts in the ops log. TARGET: this runs as a daily `maintenance` pool task.

**Caveat:** confirm the LangGraph checkpoint table names and columns for the pinned `langgraph-checkpoint-postgres` version before the first run (`\d checkpoints`). They are library-owned and excluded from Alembic (`migration_filters.include_object`).

## 4. Storage reconciliation

**CURRENT (local filesystem):**
```bash
# rows whose file is missing (run from the API container/host)
psql "$DATABASE_URL" -At -c "SELECT id, storage_path, checksum_sha256 FROM assets" |
while IFS='|' read id path sum; do
  f="$STORAGE_LOCAL_ROOT/$path"
  [ -f "$f" ] || { echo "MISSING $id $path"; continue; }
  [ "$(shasum -a 256 "$f" | cut -d' ' -f1)" = "$sum" ] || echo "MISMATCH $id $path"
done
```
**TARGET (object storage):** the daily `reconcile` maintenance task (Backup doc §4.2) writes a report and metrics.

| Result | Action |
|---|---|
| `MISSING` | Look for a previous object version (versioning) and restore it. If no version exists, set the asset `unavailable`, notify the project owner, and open a SEV-2 |
| `MISMATCH` | Quarantine the object; restore the last version whose hash matches; SEV-1 if no matching version exists (integrity) |
| Orphan object (no row, > 24 h) | Tag it; delete after 30 days unless a row claims it. Remember that rows can share one key (content-addressed), so check `SELECT count(*) FROM assets WHERE storage_path = :key` |

## 5. Provider outage → manual mode (FD-V2)

**Detect:**
- `tattva_provider_jobs_total{outcome="error"}` or 5xx/timeouts spike.
- The provider status page.
- `outcome_unknown` count rising.

**Procedure:**
1. Set the provider connection to `degraded` (admin action, audited). New `generation_jobs` for that provider default to `execution_mode=manual`, and the UI shows a banner. To force manual mode for every job, turn off `FF_PROVIDER_<ID>_CONNECTED`.
2. **In-flight attempts:** leave them in place. The provider pool keeps polling with backoff. Attempts that exceed the timeout become `outcome_unknown`. **Do not retry them.** Reconciliation runs when the provider recovers (ADR-005 rule 2), and the budget reservation is held until then.
3. **Users** use "convert to manual" (`POST /generation-jobs/{id}/convert-to-manual`) for queued jobs. They export the same package, run it in the provider's own app if it is up, or choose another verified provider, then import the result. Lineage records that the job was converted.
4. **Recovery:** run reconciliation for every `outcome_unknown` attempt; confirm there are no duplicates; move the connection back to `active`; re-enable the flag.
5. **Postmortem** if more than 10 jobs were affected or any charge is disputed.

Manual mode never depends on provider availability, so the core workflow continues.

## 6. Routine operations

| Task | Frequency | Procedure |
|---|---|---|
| Review dead letters | Daily | §1.4; every DLQ item needs a ticket or a re-drive |
| Checkpoint pruning | Daily (TARGET), weekly (CURRENT, manual) | §3 |
| Storage reconciliation | Daily | §4 |
| `pg_stat_statements` top-20 | Weekly | Look for regressions; add indexes via expand migrations |
| Dependency and CVE review | Weekly | `pip-audit` report; patch per NFR-SEC-05 |
| Secrets rotation | 90 days | DevOps §7 dual-credential rotation |
| Restore drill | Quarterly | Backup doc §7 |
| Capacity re-plan | Quarterly | Replace assumed tiers with `usage_records` data |
| Provider snapshot re-verification | Monthly per connected provider + nightly drift job | ADR-005 |
