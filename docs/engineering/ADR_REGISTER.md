# ADR Register

**Doc ID:** TFD-ENG-010 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval
**Inputs:** `docs/ADRs/*` · `docs/audit/10` (CON-02, CON-06, DEC-001…DEC-015) · `docs/implementation/OPEN_DECISIONS.md`

Per CON-06, this register and `docs/audit/10` §4 are the **single** decision record. ADRs record architectural decisions; DEC entries record open choices and approvals. An ADR is "Accepted" only after its linked approval gate is passed. The approval date and approver are added here.

## 1. Index

| ADR | Title | Status | Linked DEC / gate | Findings addressed | Requirements (traceability) |
|---|---|---|---|---|---|
| [ADR-001](../ADRs/ADR-001-greenfield-stack.md) | Greenfield technology stack and architecture | **Approved baseline** (canonical copy in `docs/ADRs/`; `docs/product/Tattva_ADR_001…` is superseded, CON-02) | DEC-001, DEC-003, DEC-004, DEC-005, DEC-008 (choices left open by ADR-001) | — | All |
| [ADR-002](../ADRs/ADR-002-frontend-strategy.md) | Frontend strategy: Streamlit alpha vs React/Next.js production workspace | Proposed: **approval gate #2** | DEC-009; CON-01, CON-04 | audit `04` §3–§4 | TFD-SCR-012, TFD-SB-001/003, TFD-OUT-002/003, TFD-SHT-001, TFD-OPS-005, NFR-A11Y-01 |
| [ADR-003](../ADRs/ADR-003-authentication-and-authorization.md) | Authentication and authorization | Proposed: **approval gate #1** | DEC-002; CODE-02 | SEC-01, 02, 03, 04, 08 | TFD-IAM-001..009, TFD-APR-002, TFD-APR-005 |
| [ADR-004](../ADRs/ADR-004-artifact-versioning-and-screenplay-lock.md) | Artifact versioning and screenplay lock | Proposed | Master Prompt §5 requirement (no DEC); DEC-010 (G-04 fix uses the locked bump) | PERF-06, CODE-07 | TFD-SCR-001..010, TFD-VER-001..005, TFD-APR-003 |
| [ADR-005](../ADRs/ADR-005-provider-registry-and-manual-first-execution.md) | Provider registry and manual-first execution | Proposed | DEC-004, DEC-006, DEC-013 (gate #7) | audit `07` §3 | TFD-INT-001..010, TFD-PKG-001..007, TFD-GEN-001..011, TFD-OUT-001 |
| [ADR-006](../ADRs/ADR-006-performer-consent-and-likeness.md) | Performer consent and likeness authorization | Proposed: **blocked on gate #6** | DEC-007, DEC-012, DEC-017 | SEC-12 | TFD-CNS-001..008, TFD-IAM-007, TFD-DH-*, TFD-VOC-003/004, TFD-PHY-006 |
| [ADR-007](../ADRs/ADR-007-outbox-hardening-vs-managed-queue.md) | Outbox hardening vs managed queue | Proposed | DEC-005 | PERF-01, 02, 04 | TFD-OPS-001..004 |
| [ADR-008](../ADRs/ADR-008-object-storage-and-media-pipeline.md) | Object storage and media pipeline | Proposed: vendor at **approval gate #5** | DEC-003, DEC-018, DEC-022 | SEC-05, PERF-03 | TFD-AST-001/002/005/006/007/010, TFD-HYB-003/004, TFD-OUT-001 |

## 2. Decisions referenced by ADRs but not yet ADRs

| DEC | Topic | Expected vehicle |
|---|---|---|
| DEC-001 | Managed PostgreSQL | Vendor selection note under DevOps; no ADR unless it changes the architecture |
| DEC-008 | Hosting | Short ADR when chosen (affects LB, secrets and IaC) |
| DEC-010 | G-04 WIP fix-forward | Phase C task, approval gate #3 |
| DEC-011 | ID scheme | Applied across Phase B docs |
| DEC-014 | Post interchange formats | Integration architecture (peer doc) |
| DEC-015 | Test DB isolation | `TESTING_AND_QA_STRATEGY.md` §6 |
| DEC-016 | Retrieval/embedding index (proposed by the AI architecture workstream) | AI_SYSTEM_ARCHITECTURE (peer doc) |
| DEC-017 | No facial embeddings or biometric templates in FD-V1/V2 (AI workstream) | ADR-006 references it |
| DEC-018 | Pinned LGPL FFmpeg/ffprobe (AI or media workstream) | ADR-008 references it |
| DEC-019 | Postgres row-level security (FD-V2), proposed by the DB workstream | DATABASE_DESIGN_AND_ERD (peer doc); complements the ADR-003 service-layer checks |
| DEC-020 | Input-fingerprint expected-version check (peer workstream) | ADR-004 §4 complements it |
| DEC-021 | Default `production_mode` backfill = `fully_ai` (peer workstream) | DATABASE_DESIGN_AND_ERD (peer doc) |

## 3. New DEC IDs proposed by the engineering workstream (to merge into `docs/audit/10` §4)

| ID | Decision | Recommendation | Approver | Source doc |
|---|---|---|---|---|
| DEC-022 | Malware scanning engine | ClamAV sidecar in the media pool for pilot; managed scanner at GA if available | Eng + Security | ADR-008, Threat model |
| DEC-023 | Observability backend | Hosting platform's managed OTel-compatible backend; Grafana stack otherwise | Eng | Observability doc |
| DEC-024 | Feature-flag mechanism | Typed `Settings` flags; per-org JSONB overrides only when the pilot needs them | Eng + Product | DevOps §9 |
| DEC-025 | Budget-gate defaults and cost approver | 80 % soft threshold; producer holds `cost.approve`; management raises limits | Product | Cost model §4 |
| DEC-026 | Pilot support hours and availability tier | Business hours, 99.5 % for pilot; 99.9 % with on-call at GA | Product + Eng | NFR §3 |

## 4. ADR template
Every new ADR copies the ADR-001 header block (Product / Decision ID / Version / Status / Date). It contains the sections: Context (with CURRENT state and code paths), Options (if more than one was considered), Decision, Consequences, Links (DEC, findings, TFD IDs). Statuses: `Proposed` → `Accepted` (date and approver) → `Superseded by ADR-xxx`.
