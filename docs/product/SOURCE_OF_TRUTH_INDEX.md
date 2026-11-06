# Tattva AI Film Director — Source of Truth Index

**Document ID:** TFD-DOC-001  
**Version:** 1.0  
**Date:** 1 November 2026  
**Status:** Approved Greenfield Baseline  

## 1. Document Inventory and Status

| Document | File Name | Version | Status | Role & Precedence |
|---|---|---|---|---|
| **Product Requirements Document (PRD)** | `Tattva_AI_Film_Director_PRD_v0.9.md` | v0.9 | Active Baseline (Technical Section amended by ADR-001) | Highest authority for product scope, functional requirements, domain concepts, and business rules. |
| **Information Architecture (IA)** | `Tattva_AI_Film_Director_IA_v1.0.md` | v1.0 | Active Baseline | Controlling authority for navigation structure, 44 screen inventory (8 global + 36 project), user journeys, and Streamlit page organization. |
| **Wireframe & UI Component Spec** | `Tattva_AI_Film_Director_Wireframe_Spec_v1.0.md` | v1.0 | Active Baseline | Controlling authority for layout composition, visual tokens, UI components, states, responsive rules, and interaction patterns. |
| **HTML Wireframe Preview** | `Tattva_AI_Film_Director_Wireframe_Preview_v1.0.html` | v1.0 | Interactive Reference | Visual reference for screen layout and component composition. |
| **Greenfield Architecture Addendum** | `Tattva_AI_Film_Director_Greenfield_Architecture_Addendum_v1.1.md` | v1.1 | Active Technical Baseline | Controlling authority for technical architecture, LangGraph orchestration, domain layering, persistence, runtime boundaries, and implementation sequence. |
| **Architectural Decision Record 001** | `docs/ADRs/ADR-001-greenfield-stack.md` (and root `Tattva_ADR_001_Greenfield_Stack_v1.0.md`) | v1.0 | Approved Baseline | Records Streamlit + FastAPI + LangGraph + selective LangChain + PostgreSQL + Modular Monolith + Worker stack. |
| **Company Architecture Baseline** | `Tattava_Copilot_Architecture_Blueprint_Revised_v2.0` | v2.0 | Reference | Company-wide governance and separation of deterministic controls from AI cognition. |
| **Visual Assets** | `a_wide_composite_ui_mockup_tattva_ai_film_directo.png`<br>`tattva_greenfield_architecture_diagram.png`<br>`tattva_script_intelligence_flow.png` | v1.0 | Reference Assets | Visual direction board, target architecture diagram, and Script Intelligence flow. |

## 2. Precedence and Conflict Resolution Hierarchy

1. **Product scope and requirements:** PRD v0.9.
2. **Navigation and user journeys:** IA v1.0.
3. **Screen layouts and UI behaviour:** Wireframe Specification v1.0.
4. **Backend, AI runtime, and persistence boundaries:** Greenfield Architecture Addendum v1.1 and ADR-001.
5. **Company-wide product governance:** Tattva strategy and revised architecture baseline.

### Resolved Discrepancies
- **UI Framework Conflict:** PRD v0.9 proposed Next.js/React in section 10, whereas IA v1.0 and Wireframe Spec v1.0 explicitly specify desktop-first Streamlit. As resolved in ADR-001, **Streamlit** is the selected UI direction for this workstream.

## 3. Missing or External Items

The following items are external or unprovisioned at this stage:
- **Live Model Provider Credentials:** Unconfigured (provider-neutral gateway with deterministic mock adapters used for development and local testing).
- **Managed Auth Provider:** Provider-neutral auth boundary with project/organization context tokens; external SSO/Supabase Auth to be configured upon production provisioning.
- **Hosted Object Storage:** Local private file store / S3-compatible adapter interface implemented; cloud bucket (S3/Supabase Storage) not yet provisioned.
- **Higgsfield Live API Contract:** Higgsfield is an external environment; manual export/import package format implemented until a verified external integration contract is established.
- **Managed Production Database:** Dedicated PostgreSQL with pgvector (local container `pgvector/pgvector:pg16` active on port 55432).

---

## Change Note — 2026-11-05 (Product Evolution audit, Phase A/B)

This note **supersedes the precedence above**. The original text is kept for history.

**New precedence (Master Execution Prompt §2.3):**
1. Explicit decisions in the Master Execution Prompt (2026-11).
2. `Tattva_AI_Film_Director_Product_Evolution_Implementation_Gap_Report_v1.0.docx` (external; text not in repo).
3. `docs/product/PRD_v1.0.md` once approved. Until then, PRD v0.9 together with the Master Prompt.
4. Approved ADRs: `docs/ADRs/` (canonical location; the `docs/product/Tattva_ADR_001…` copy is superseded).
5. Architecture and engineering docs in `docs/architecture/` and `docs/engineering/`.
6. Repository implementation, as audited in `docs/audit/`.

**New documents:**
- `docs/audit/00–10`: audit and decision register.
- `docs/product/`: PRD_v1.0, PRODUCT_ROADMAP, REVISED_USER_JOURNEYS, INFORMATION_ARCHITECTURE, SCREEN_INVENTORY_AND_BEHAVIOUR, ACCEPTANCE_CRITERIA.
- `docs/architecture/*`, `docs/engineering/*`, `docs/release/*`.
- ADR-002 to ADR-008.

**Corrections to statements above (verified against code on 2026-11-05):**
- "Manual export/import package format implemented": **not implemented**. Higgsfield exists as configuration only (`packages/core/config.py`).
- "S3-compatible adapter interface implemented": **only** `LocalFileSystemStorageService` exists. An S3-compatible adapter is not implemented.
- "Provider-neutral auth boundary with project/organization context tokens": the code uses an unauthenticated `X-Actor-ID` header (`packages/services/identity.py`). See `docs/audit/08` SEC-01.
- Referenced `Tattava_Copilot_Architecture_Blueprint_Revised_v2.0` is not in the repo (CON-07).
- ID collision: "G-0x" denotes screens in the IA but graphs in the Addendum and the code. New IDs are `S-*` for screens and `WF-*` for workflows (DEC-011).

Full conflict list: `docs/audit/10_DOCUMENT_CONFLICT_AND_DECISION_REGISTER.md`.

---

## Change Note — 2026-11-06 (S0: IA v1.1 and Journey manifest)

**Controlling UI/UX authority.** For navigation, layout, interaction and visual tokens, the **Guided Workspace UX package** in `docs/product/ux/guided-workspace-v1.0/` replaces Wireframe Spec v1.0, the v1.0 Wireframe Preview and the earlier Streamlit page organisation. The package is:
- `Tattva_AI_Film_Director_UX_Strategy_Guided_Workspace_v1.0.md` (and `.docx`)
- `Tattva_AI_Film_Director_Guided_Workspace_Wireframe_v1.1.html`
- `tattva_guided_workspace_preview.png`

Where the UX strategy and Wireframe v1.1 differ, **Wireframe v1.1 wins** because it is newer.

| Document | File | Version | Role |
|---|---|---|---|
| Information Architecture | `docs/product/INFORMATION_ARCHITECTURE.md` | v1.1 | Primary navigation (Online Workspace → 10-section journey), the canonical 61-screen catalogue as Studio Tools, legacy ID aliases, release view, and the shell and token baseline (§0) |
| Journey Manifest (spec) | `docs/product/JOURNEY_MANIFEST.md` | v1.0 | Identity, applicability, status, completion and gating rules for the journey. Tables are generated from the YAML |
| Journey Manifest (data) | `packages/domain/journey_manifest.yaml` | v1 | Machine-readable journey content. GW1 and GW2 build from it. `tests/unit/test_journey_manifest.py` checks it against the wireframe, PRD, IA and capability catalogue |

**Frontend:** React replaces Streamlit (ADR-002, amended at plan approval on 2026-11-06). This supersedes the "UI Framework Conflict" resolution in §2 above.
