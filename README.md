# Tattva AI Film Director

Tattva is a project-centric filmmaking intelligence workspace. A filmmaker starts with a
blank idea or an existing project — scripts, storyboards, character sheets, reference
videos, stills, environment designs, historical research, audio references, director
notes and previously generated footage.

Tattva understands those materials, identifies how they relate, inspects them for gaps
and contradictions, researches historical context, builds a persistent **Film Bible**
and continuity model, plans scenes and shots, compiles production instructions, and
hands off approved packages to generation providers (Higgsfield and others) — with a
human approval gate at every step where AI proposes something to canon.

## Status

FD-V1 (first full production release) is in active build-out, following
[`docs/implementation/FINAL_GRADE_IMPLEMENTATION_PLAN.md`](docs/implementation/FINAL_GRADE_IMPLEMENTATION_PLAN.md)
section by section. Each milestone lands as a complete vertical slice — UI, API,
authorization, service, database, approval gate, audit trail, and tests — before the
next one starts. Current progress and what's deferred (with the reasoning for every
judgment call) is tracked in
[`docs/audit/10_DOCUMENT_CONFLICT_AND_DECISION_REGISTER.md`](docs/audit/10_DOCUMENT_CONFLICT_AND_DECISION_REGISTER.md).

| Stage | Covers | Status |
|---|---|---|
| D1 | Project Workspace & Setup | Done |
| D2 | Screenplay & Governance | Done |
| D3 | Story Intelligence v2 (dialogue, characters, locations, golden set) | Done |
| D4 | Character & Digital Human (V1 foundation) | Done |
| D5 | Visual World | Next |

## Architecture

A Python/FastAPI backend, a React/TypeScript frontend, PostgreSQL for canonical storage,
and LangGraph for the AI workflows that propose candidates for human review.

```
apps/
  api/      FastAPI application — routers, schemas, dependency injection, error mapping
  worker/   Background worker: claims queued workflow runs (lease/retry/dead-letter)
  web/      React + TypeScript frontend (Vite, TanStack Query, React Router)
  ui/       Legacy Streamlit alpha surface — superseded by apps/web, kept until the
            Playwright E2E suite (DEC-031/033) is in place to safely retire it

packages/
  ai/         ModelGateway: one typed interface over every AI capability (today backed
              by deterministic generators; a real LLM provider is a config change away)
  core/       Settings, logging, tracing — the only place environment variables are read
  domain/     Enums, capabilities/RBAC catalogue, errors, the Guided Workspace journey
              manifest — the vocabulary every other package imports
  persistence/ SQLAlchemy models, repositories (the only layer that issues SQL), and
              Alembic migrations
  services/   Business logic: one service class per feature area, authorization enforced
              here (not in routers), one commit per use case
  storage/    Object storage adapter (local filesystem today, S3-compatible behind the
              same interface) and malware-scan seam
  workflows/  LangGraph graphs: script intelligence, historical research, storyboard
              intelligence, film bible synthesis, screenplay suggestions

tests/      pytest (backend) — unit, api, workflows, integration, golden-set fixtures
docs/       Product, architecture, engineering and audit documentation (see below)
```

**Core patterns used throughout**, so any new feature should follow the existing ones
rather than reinvent them:
- **Candidate → human approval → canon.** Every AI-proposed change lands as a
  `*_candidate` row first; nothing becomes canonical without an explicit approval
  decision, recorded in an append-only audit trail.
- **Authorization in services, not routers.** `AuthzService.require(actor, capability,
  project)` is called from the service method performing the action, which already has
  the project loaded and knows precisely what's being attempted.
- **Expand → backfill → contract** migrations for any new `NOT NULL` column on a
  non-empty table; named foreign-key constraints always, so `downgrade()` works.
- **Generalized approval targets.** `approval_requests.target_type`/`target_id` let a
  new decision type (a screenplay lock, a character version, a consent record) reuse the
  same approval machinery instead of a bespoke table per feature.

## Getting started

Requirements: Python 3.11+, Node 20+, Docker (for PostgreSQL), and `uv`/`pip`.

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # fill in local secrets as needed
docker compose up -d db         # PostgreSQL
alembic upgrade head
uvicorn apps.api.main:app --reload

# Frontend
cd apps/web
npm install
npm run dev
```

Or run the full stack (API, worker, web, PostgreSQL) containerized:

```bash
docker compose up -d --build
```

### Running tests

```bash
# Backend — uses a dedicated <db>_test database, never the dev database
pytest
ruff check .

# Frontend
cd apps/web
npm run lint
npx tsc -b
npm test
```

Every backend migration is expected to round-trip cleanly:

```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

## Documentation map

`docs/` is organized by audience and lifecycle stage:

| Folder | Contents |
|---|---|
| [`docs/product/`](docs/product/) | PRD, roadmap, user journeys, information architecture, screen specs, acceptance criteria — the product source of truth. Start at [`SOURCE_OF_TRUTH_INDEX.md`](docs/product/SOURCE_OF_TRUTH_INDEX.md). |
| [`docs/architecture/`](docs/architecture/) | System, database, API/event contracts, and domain-specific architecture docs (AI, character/digital human, cinematography, hybrid production, integrations). |
| [`docs/ADRs/`](docs/ADRs/) | Architecture Decision Records — numbered, one decision each. |
| [`docs/engineering/`](docs/engineering/) | NFRs, security, testing strategy, observability, deployment, requirement-to-code traceability. |
| [`docs/audit/`](docs/audit/) | The original gap-analysis audit, plus [`10_DOCUMENT_CONFLICT_AND_DECISION_REGISTER.md`](docs/audit/10_DOCUMENT_CONFLICT_AND_DECISION_REGISTER.md) — every scope judgment call made during the build, with its reasoning, kept current as the build progresses. |
| [`docs/implementation/`](docs/implementation/) | [`FINAL_GRADE_IMPLEMENTATION_PLAN.md`](docs/implementation/FINAL_GRADE_IMPLEMENTATION_PLAN.md) is the authoritative build log: what's done, how, and what tests prove it. |
| [`docs/release/`](docs/release/) | Launch plan, release readiness checklist, operations and incident-response runbooks. |

When a product document and the acceptance criteria disagree, `ACCEPTANCE_CRITERIA.md`
and the decision register are authoritative — both are kept current as the build
progresses, unlike the earlier narrative product docs.
