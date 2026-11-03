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
