# ADR-001 — Greenfield Technology Stack & Architecture

**Product:** Tattva AI Film Director  
**Decision ID:** ADR-001  
**Version:** 1.0  
**Status:** Approved Greenfield Baseline  
**Date:** 1 November 2026  

## Context

Tattva AI Film Director is a new product being built from scratch. There is no current Tattva application, legacy repository, production database schema or deployment pipeline to audit or preserve. The product must support a complex filmmaking intelligence lifecycle with persistent project context, source-grounded research, asset intelligence, continuity, AI workflows, human approvals and external Higgsfield handoff.

The PRD v0.9 technical section mentions Next.js/React, while the later IA v1.0 and Wireframe Specification v1.0 explicitly target Streamlit. For this greenfield workstream, Streamlit is selected as the UI direction and the PRD is amended accordingly.

## Decision

Adopt the following initial architecture:

| Layer | Decision | Rationale |
|---|---|---|
| **UI** | Streamlit | Matches the latest IA and wireframe baseline; appropriate for a Python-first internal production workspace and early vertical slice |
| **Application API** | FastAPI / Python | Explicit API boundary for auth, project commands, approvals, workflow lifecycle and integrations |
| **AI workflow orchestration** | LangGraph / Python | Stateful workflows, branching, checkpointing, interrupt/resume and human review |
| **LLM/tool building blocks** | LangChain selectively | Use concrete components when useful; not mandatory for every model operation |
| **Architecture style** | Modular monolith | Avoid premature distributed services; keep UI, API and worker as separate processes with shared domain packages |
| **Canonical data** | Dedicated PostgreSQL database | Durable source of truth for project entities, versions, approvals and audit history |
| **Semantic retrieval** | pgvector where justified | Reuse PostgreSQL and enforce project/tenant metadata filters |
| **Long-running execution** | Separate worker process with durable dispatch | Keep media/AI processing outside Streamlit request execution; start with a PostgreSQL outbox/claiming pattern |
| **Workflow recovery** | LangGraph PostgreSQL checkpointer, isolated from canonical project tables | Durable resume without confusing checkpoint state with project truth |
| **File storage** | Private object storage | Preserve immutable originals and derived artifacts with controlled access |
| **Video generation** | External Higgsfield environment | Tattva prepares/inspects packages; it does not render video internally |

## Architectural Invariants

1. Project Intelligence / Story Brain and canonical domain services remain the system of record.
2. LangGraph orchestrates AI work; it does not own authentication, authorization, business policy or canonical writes.
3. All AI outputs are candidates until validated and approved where required.
4. Human approval is recorded in Tattva's approval service before a graph is resumed or canonical state is mutated.
5. Every project-scoped operation rechecks organization, project, actor and object permissions.
6. Graph state stores compact references and execution metadata, not full project history or large media payloads.
7. External provider actions are idempotent/reconciled and require explicit approval where they incur credits or have irreversible effects.
8. Model and storage providers remain replaceable behind adapters.

## Consequences

- The PRD technical section is formally amended to replace Next.js/React with Streamlit.
- A new repository, application scaffold, database, migrations, object-storage configuration and worker runtime are created.
- An API/OpenAPI contract, initial ERD/schema and graph contracts are delivered fresh.
- The first build milestone is the platform foundation plus one Script Intelligence vertical slice.
- Authentication provider, managed PostgreSQL host, object storage, model provider, deployment target and production queue remain explicit decisions behind provider-neutral interfaces.
