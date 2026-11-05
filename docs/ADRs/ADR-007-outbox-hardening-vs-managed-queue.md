# ADR-007 — Outbox Hardening vs Managed Queue

**Doc ID:** ADR-007 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval
**Inputs:** Master Prompt §20.4, §20.7 · `docs/audit/03` §8, `06` §3, `08` PERF-01/04 · `apps/worker/worker.py` · `packages/persistence/repositories.py::OutboxRepository` · `packages/persistence/models.py::OutboxTaskModel` · DEC-005

**Product:** Tattva AI Film Director
**Decision ID:** ADR-007
**Version:** 1.0-draft
**Status:** Proposed
**Date:** 5 November 2026

## Context

**What works today:** `outbox_tasks` rows are inserted in the same transaction as `workflow_runs`, so enqueueing is transactional. `claim_next` uses `FOR UPDATE SKIP LOCKED` on the oldest pending row, which is safe with several workers.

**Defects:**
- Any exception means the task is `failed` forever. There is no retry, backoff or DLQ.
- A task claimed by a crashed worker is never reclaimed, because there is no lease.
- Redelivery restarts the graph from START, duplicating candidates.
- One task per process; `WORKER_CONCURRENCY` is declared but unused.
- One pool for every workload.
- `workflow_run_id` is **unique** on `outbox_tasks`, so only one task per run is possible.
- Workflows run synchronously in HTTP by default (PERF-01).

**Options:**
- (A) harden the Postgres outbox
- (B) move to a managed queue (SQS, Pub/Sub, etc.) or Redis-based Celery/ARQ
- (C) adopt a durable-execution engine

## Decision (proposed)

**Option A: harden the outbox.** Revisit only on the triggers below.

### Changes (all additive)
| Change | Detail |
|---|---|
| Columns | `lease_expires_at`, `next_attempt_at` (default now), `max_attempts` (default 5), `dedupe_key` (unique), `last_error_class`, `last_error` (truncated), `dead_lettered_at`, `pool` (default `graph`), `task_kind` (default `start`), `heartbeat_at` |
| Statuses | Add `dead_lettered` (statuses are strings, so no enum migration is needed); `failed` remains for legacy rows |
| Unique constraint | Expand: add `dedupe_key` unique; backfill `'start:'||workflow_run_id`. Contract later: drop the unique on `workflow_run_id`, which allows resume/poll/reconcile tasks per run |
| Claim | `WHERE pool=:pool AND ((status='pending' AND next_attempt_at<=now()) OR (status='claimed' AND lease_expires_at<now())) ORDER BY next_attempt_at LIMIT 1 FOR UPDATE SKIP LOCKED`; sets the lease. Partial index `(pool, next_attempt_at) WHERE status IN ('pending','claimed')` |
| Heartbeat | Every `lease/3`; if the heartbeat fails (row stolen) the handler aborts at the next node boundary |
| Retry | Error classes: `retryable` (transient DB/network, provider 5xx/429), `non_retryable` (validation, authZ, consent deny), `outcome_unknown` (provider timeout; reconcile first). Full-jitter exponential backoff, base 10 s, cap 15 min |
| DLQ | `dead_lettered` + `dead_lettered_at`; the run goes to `failed` with a reason; audited operator re-drive |
| Resume semantics | The handler checks for a checkpoint for `thread_id=run_id`: if present it calls `invoke(None, config)`; otherwise it starts fresh. Candidate inserts are idempotent on `(workflow_run_id, ordinal)` |
| Async by default | `sync_execution` default becomes `False` behind `FF_ASYNC_WORKFLOWS` (the field stays in the request schemas; tests may still pass `True`) |
| Approval resume | Moves from the HTTP request to a `resume` task |
| Pools | `graph`, `media`, `provider`, `maintenance`; `--pool` CLI flag; per-pool concurrency and timeouts |
| Shutdown | SIGTERM → stop claiming → finish or release |
| Cancellation | `workflow_runs.status='cancel_requested'` checked between nodes and before submits |
| Backpressure | API 429 above the per-pool high watermark or per-project active-run limit |

### Why not a managed queue now
- **Transactional enqueue** is the property that keeps runs, approvals and tasks consistent. A broker needs its own outbox relay to regain it, which adds a component without removing one.
- Expected load (capacity plan §6: ~500 runs/day; peak 5,000) is far below what `SKIP LOCKED` handles on modest PG.
- One fewer stateful system to secure, back up and monitor.

### Triggers to revisit (any one)
- p95 claim latency > 1 s at saturation after index tuning.
- Sustained > 50 tasks/s.
- A need for cross-region workers.
- Outbox table bloat that autovacuum cannot hold, after a 7-day retention of completed rows.

When a trigger fires, the migration path is an outbox **relay** (the outbox stays the source; a relay publishes to the broker), so producers do not change.

## Consequences

- Fixes PERF-01, PERF-04, NFR-JOB-04/05.
- Requires the crash tests in Testing §8.
- Completed rows are pruned after 7 days by a maintenance task; `workflow_runs` keeps the history.
- Graph code must tolerate replay of a node (idempotent writes). This is a coding rule for all WF graphs.

## Links
DEC-005 · PERF-01, PERF-02, PERF-04 · `SCALABILITY_PERFORMANCE_CAPACITY_PLAN.md` §4 · `PRODUCTION_OPERATIONS_RUNBOOK.md` §1
