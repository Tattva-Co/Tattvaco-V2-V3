# ADR-006 — Performer Consent and Likeness Authorization

**Doc ID:** ADR-006 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval
**Inputs:** Master Prompt §6.2–§6.5, §9 (voice), §21 · `docs/audit/02` §3, `08` SEC-12 · DEC-007, DEC-012, DEC-017 · `DATA_PRIVACY_AND_RETENTION.md` · `SECURITY_THREAT_MODEL.md` §3.1

**Product:** Tattva AI Film Director
**Decision ID:** ADR-006
**Version:** 1.0-draft
**Status:** Proposed. Implementation of any C4 storage is **blocked** until DEC-007 and DEC-012 (approval gate #6) are approved.
**Date:** 5 November 2026

## Context

- No performer, consent, likeness or voice model exists (SEC-12).
- The Master Prompt §6.5 requires consent before any of these: creating digital doubles or AI avatars, deriving appearance models, using performance footage for transformation, cloning voices, generating new performances, and reusing likeness in future projects.
- The consent must be explicit, purpose-specific, versioned, traceable, revocable, and linked to performer and project permissions.
- Access to sensitive identity references must itself be authorized.

## Decision (proposed)

### 1. Model (DB design owns final columns)
- `performers`: a real person. Includes `legal_name` (C4), `display_name`, and optionally an agent/representative contact. Distinct from fictional `characters`. A character may link to zero or more performers by role (`face_source`, `body_source`, `performance_source`, `voice_source`).
- `performer_consents`: one row per consent **version**. Fields include:
  - `performer_id`, `organization_id`
  - `project_scope` (a specific project ID, or a list)
  - `purposes[]`
  - `allowed_providers` (null = any verified provider passing disclosure)
  - `territory_and_term` (free text plus `valid_from` / `valid_until`)
  - `status ∈ {draft, active, suspended, revoked, expired}`
  - `document_asset_id` (signed agreement, C4)
  - `template_version` (Legal-owned, DEC-012)
  - `recorded_by`, `verified_by` (Legal role)
  - `supersedes_id`
- **Purposes (closed enum, extended only by migration):** `capture_reference`, `create_digital_double`, `create_fictional_avatar_from_performer`, `derive_appearance_model`, `performance_transformation`, `voice_clone`, `voice_synthesis_new_lines`, `generate_new_performance`, `reuse_in_project`, `evaluation`.
- Approval: activating or changing a consent creates `approval_requests(approval_level=consent)`, decided by a `consent.manage` holder (ADR-003).

### 2. Gate
`ConsentPolicy.check(performer_ids, purpose, project_id, provider_id | None, at=now) → Allow | Deny(reason)` is a pure domain function with exhaustive unit tests. It is invoked at:
1. Creation of `digital_humans`, `avatar_versions` and `voice_profiles` derived from a performer.
2. Upload or link of C4 references to a performer (`capture_reference`).
3. Package compile (`production_packages`) when the shot references performer-derived assets.
4. **Immediately before provider submit** in the worker (ADR-005 rule 1).
5. Manual package export containing C4 references.

The gate fails closed: unknown performer linkage on a C4 asset counts as `Deny`. `FF_CONSENT_ENFORCEMENT` cannot be disabled in production (DevOps §9).

### 3. Access control to C4 data
- `likeness.view` / `voice.view` capabilities. C4 bytes are served only via the API; every read is audited.
- No facial embeddings or biometric templates are created (**DEC-017**).

### 4. Revocation
Revocation propagates as in `DATA_PRIVACY_AND_RETENTION.md` §4.2:
- non-terminal jobs are blocked
- derived assets are flagged `consent_revoked`
- provider deletion requests are made where the provider supports them (UNVERIFIED per provider)
- an impact report is produced for human decision on already-approved material (**OPEN — DEC-012**)

### 5. Estimated vs verified identity data
Body measurements from AI estimation carry `verification_status=estimated` and cannot be used where a shot spec requires `verified` measurements (Master Prompt §6.4).

## Consequences

- Digital human, voice and performance-transformation features (TFD-DH-*, TFD-VOC-*, TFD-PHY-*) all depend on this ADR. FD-V1 builds the model and gate; FD-V2 uses them.
- Adds legal process dependencies: template, verification role, DPIA (Privacy doc §6).
- Non-real-person (fictional) characters are unaffected and can proceed without this gate.

## Links
DEC-007 · DEC-012 (gate #6) · DEC-017 · SEC-12 · ADR-003 · ADR-005 · TFD-CNS-001..008, TFD-IAM-007, TFD-PKG-007
