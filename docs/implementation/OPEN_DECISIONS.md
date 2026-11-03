# Open Architecture & Product Decisions Register

**Product:** Tattva AI Film Director  
**Document ID:** TFD-DEC-002  
**Version:** 1.0  
**Date:** 1 November 2026  
**Status:** Greenfield Decisions Register  

This register tracks all unresolved technology, provider, infrastructure, and governance choices. As specified in the Greenfield Architecture Addendum v1.1, all unselected providers use clean abstraction adapters and deterministic local mocks so development progress is never blocked.

---

## 1. Decision Inventory

| ID | Area | Current Status / Default Choice | Options Under Evaluation | Impact & Reversibility | Next Gate |
|---|---|---|---|---|---|
| **DEC-001** | **Managed PostgreSQL Provider** | Local Docker `pgvector/pgvector:pg16` on port 55432; standard SQLAlchemy + Alembic ORM interface. | Supabase, AWS RDS PostgreSQL, Neon, Self-hosted PostgreSQL. | Low impact / Highly reversible via standard PostgreSQL connection string and SQLAlchemy models. | Before staging deployment. |
| **DEC-002** | **Authentication Provider** | Header/Token-based identity boundary (`X-Actor-ID`, `X-Org-ID`, `X-Project-ID`) enforced via FastAPI dependency injection. | Supabase Auth, Clerk, Auth0, Okta. | Low impact / Reversible behind FastAPI `get_current_actor` dependency. | Multi-user staging setup. |
| **DEC-003** | **Object Storage Provider** | Local filesystem storage service implementing `StorageService` protocol (immutable paths, SHA-256 integrity). | Supabase Storage, AWS S3, Cloudflare R2, MinIO. | Highly reversible behind `StorageService` interface. | Staging deployment. |
| **DEC-004** | **Model Gateway & LLM Provider** | Provider-neutral Gateway with deterministic mock/fixture adapter for local tests. | OpenAI (GPT-4o), Anthropic (Claude 3.5 Sonnet), Google Gemini (1.5 Pro / 2.0 Flash), Local Ollama. | Medium impact / Abstracted behind `ModelGateway` interface. No vendor lock-in. | Model evaluation spike. |
| **DEC-005** | **Production Queue & Worker Dispatch** | PostgreSQL-backed durable outbox/task-claiming table with optimistic row locking (`FOR UPDATE SKIP LOCKED`). | Redis + Celery/ARQ, AWS SQS, PostgreSQL Outbox. | Low initial complexity; zero extra infra dependencies. Queue adapter allows swap if throughput demands. | High-concurrency benchmark. |
| **DEC-006** | **External Video Generation (Higgsfield)** | Provider-neutral shot package schema + manual package export/import JSON + Mock Higgsfield adapter. | Higgsfield API (when contract verified), manual export/import, alternative video engines. | Zero risk. Strictly respects product boundary: Tattva does not generate video internally. | Partner API discovery / contract signoff. |
| **DEC-007** | **Data Retention & Privacy Policy** | Immutable original files retained indefinitely per project; graph state references only; checkpoint pruning policy. | Configurable project-level TTL, strict deletion on project archive, GDPR export. | Policy decision required before customer onboarding. | Pre-production security review. |
| **DEC-008** | **Hosting & Deployment Target** | Docker Compose / containerized processes (Streamlit on :8501, FastAPI on :8000, Worker loop). | Fly.io, AWS ECS/Fargate, Render, Kubernetes. | High portability via standard Docker containers. | Production operations review. |

---

## 2. Invariants for Open Decisions

1. **No Mock Credential Leakage:** No real or fake secrets are ever stored in source control.
2. **Provider Independence:** All domain logic and LangGraph state depend strictly on internal abstractions (`StorageService`, `ModelGateway`, `ApprovalService`, `RunDispatcher`), never direct third-party SDK calls.
3. **No Fake Success:** When a provider is unconfigured or operating in mock mode, the system surfaces this explicitly in metadata, logs, and UI indicators.
