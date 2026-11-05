# 11 — Approval Gate Decisions

**Doc ID:** TFD-AUDIT-011 · **Date:** 2026-11-06 · **Approver:** Kaustubh Deshmukh (product owner)
**Basis:** On 2026-11-06 the product owner instructed that every gate and blocker be auto-approved using the recommendation recorded in `10_DOCUMENT_CONFLICT_AND_DECISION_REGISTER.md` §4. This file records each resulting decision.

"**Approved — external dependency**" means the engineering direction is approved, but delivery still needs something only a human or organisation can supply, such as a vendor account, an API key or a legal document. Engineering proceeds with the vendor-neutral port and a clearly labelled local or mock adapter until that input arrives. **Nothing is faked as live.**

## 1. Approval gates

| Gate | Decision | Approved direction | External dependency still needed | Unblocks |
|---|---|---|---|---|
| 1 | DEC-002 Authentication | An `AuthProvider` port with JWT verification inside `get_actor`. In **local/dev**, a built-in dev token issuer (HS256, `SECRET_KEY`) with an explicit dev login. In **staging/prod**, OIDC with JWKS verification. `ENVIRONMENT` fails closed. Header identity is allowed **only** in `test`. | Choice of OIDC vendor (e.g. Auth0, Clerk, Keycloak, Cognito) before staging | C3 |
| 2 | DEC-009 Frontend (ADR-002) | **Amended by the product owner on 2026-11-06: React replaces Streamlit now.** The new app is Vite + React + TypeScript in `apps/web`, implementing the Guided Workspace UX at production grade. Streamlit (`apps/ui`) is frozen, then deleted once `apps/web` reaches parity with it (verified by Playwright E2E). | — | GW, all UI work |
| 3 | DEC-010 G-04 WIP | **Fix forward.** Commit the user's WIP together with fixes for G04-A/B/C/H/I and regression tests. D (manual canon writes) goes through approval in C8. | — | C1 |
| 4 | DEC-004 Model gateway / LLM | Build the `ModelGateway` port with the deterministic adapter (labelled `deterministic` / `mock` in the API and UI) and golden-set skeletons first. The live LLM provider is chosen by an evaluation on the golden sets. | LLM provider API key and evaluation budget | C10, then D3/D4/D5 AI quality |
| 5 | DEC-003 Object storage | An S3-compatible adapter behind the existing `StorageService`, with **MinIO in local docker-compose**, presigned and streaming upload, and the local filesystem kept for tests. | Cloud bucket before staging | C7 |
| 6 | DEC-012 + DEC-007 Consent / retention | Legal owns the consent template and retention schedule. Engineering builds the consent model and its enforcement points now. **Hard rule:** no real performer likeness, measurement or voice data is ingested until a Legal-approved template version is recorded in the system. Until then the gate blocks with a clear reason. | Legal consent template + retention schedule | D5 (model) now; real data later |
| 7 | DEC-013 First connected provider | One image provider with an official API, chosen after a terms/legal review. Midjourney stays **manual-only**. Connected mode remains disabled per provider until that provider's review is recorded. | Terms review + provider account | E1/E2 (FD-V2) |
| 8 | DEC-027 Role & capability matrix | Deny-by-default capabilities. Role templates (from UX §12): `management_approver`, `project_owner`, `director`, `writer`, `cinematographer`, `producer`, `production_coordinator`, `ai_artist`, `research_specialist`, `performer`, `sound_specialist`, `post_recipient`, `viewer`. Approval authority is a **separate grant**. `screenplay.approve_lock`, `consent.manage`, `cost.approve` and `continuity.approve_canon` are never implied by any role except where explicitly granted. | — | C4, D2 |

## 2. Other decisions approved as recommended

| ID | Decision |
|---|---|
| DEC-001 | Managed Postgres 16 with pgvector and PITR. The vendor is chosen at staging. |
| DEC-005 | Keep the Postgres outbox, adding lease, retry with jitter and a DLQ (ADR-007). |
| DEC-006 | Higgsfield runs in manual package mode first. API and MCP become separate adapters after contract verification. |
| DEC-008 | One Dockerfile per process (api, worker, ui). Hosting is on a managed container platform, with no Kubernetes until it is justified. |
| DEC-011 | ID scheme: `S-*` screens, `WF-*` workflows, `TFD-<AREA>-nnn` requirements. The Guided Workspace adds stable `JRN-<section>.<group>.<item>` step IDs whose display numbers are derived. |
| DEC-014 | JSON and CSV manifests come first. OTIO, EDL or XML only after a validated round-trip in Resolve or Premiere. |
| DEC-015 | Dedicated per-session test database. |
| DEC-016 | No embeddings or retrieval index in FD-V1. |
| DEC-017 | No facial embeddings or biometric templates in FD-V1/V2. |
| DEC-018 | Pinned LGPL ffprobe/FFmpeg in the worker image (licence review noted). |
| DEC-019 | Postgres row-level security in FD-V2, after the `organization_id` backfill. |
| DEC-020 | Expected-version check on an input fingerprint instead of the project-wide version. |
| DEC-021 | Backfill `production_mode = fully_ai` on existing projects; owners confirm. |
| DEC-022 | ClamAV sidecar for upload scanning. Until it is deployed, uploads stay in a `quarantined → clean` state machine using a labelled no-op scanner in dev. |
| DEC-023 | OpenTelemetry SDK with OTLP export, so the backend is vendor-neutral. Local setup: console exporter plus structured JSON logs. |
| DEC-024 | Feature flags live as environment/DB-backed settings (`feature_flags` table), with no SaaS. |
| DEC-025 | Budget gates default to no spend without explicit `cost.approve`. Per-project cap is set by the project owner. |
| DEC-026 | Pilot support: business hours, best-effort. Revisit at GA. |
| DEC-028 | The pilot uses one historical short (hybrid) and one fully-AI short. Template defaults come from PRD v1.0 §10. |
| DEC-029 | Creative branches are deferred. The hardcoded "Branch: main" label is removed. |

## 3. Conflicts resolved by the new UX strategy (2026-11-06)

- **CON-04 (screen count, 26 / 36 / 44 / 60).** The Guided Workspace UX v1.0 is the newest product-owner input. Its **10-section journey is the canonical navigation**. The 36 detailed wireframe screens and the 60 canonical screens from `INFORMATION_ARCHITECTURE.md` become contextual **Studio Tools** under those sections. The IA moves to v1.1 with that mapping, and no capability is deleted.
- **Prototype progress in localStorage** stays a prototype only. Journey progress, applicability, completion events and staleness are server-side records (new `journey_*` tables).
