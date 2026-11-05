# AI System Architecture

**Doc ID:** TFD-ARCH-AI-001 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval

**Inputs:** Phase A audit `docs/audit/01`, `02`, `06`, `07`, `10`; Gap Report v1.0 (§7, §9 AI data model rows); Greenfield Addendum v1.1 §5 (LangGraph rules), §6 (graph catalogue), §11 (failure classes/telemetry/eval gates); `docs/implementation/OPEN_DECISIONS.md` DEC-004; code in `packages/workflows/*`, `packages/services/*review*.py`, `packages/services/{script_intelligence,historical_research,storyboard,film_bible}.py`, `packages/core/config.py`, `apps/worker/worker.py`.

> **Source note.** Field lists reconciled against the Master Prompt field digest (2026-11-05). §11 covers every §22 metric and tracking item. §10 covers the §5 rule that AI cannot silently change the screenplay.

---

## 1. Purpose and boundaries

This document defines how Tattva uses AI models: the gateway that hides providers, the deterministic Context Resolver that feeds them, where LangGraph is (and is not) used, how outputs are validated and kept out of canon, and how quality, cost and behaviour are measured.

It does **not** cover external media generation providers (image/video/voice/lip-sync). Those are execution targets reached through the integration layer (`INTEGRATION_ARCHITECTURE.md`). Tattva never generates media itself. The AI layer here produces **text and structured candidates**, such as extractions, research claims, rules, shot candidates, review findings and compiled prompts.

### 1.1 Current state vs target, at a glance

| Concern | CURRENT (as-built, audit 06) | TARGET (this design) |
|---|---|---|
| Model access | None. `packages/core/config.py` declares `model_gateway_provider: Literal["mock"]` plus three unused API-key fields | `ModelGateway` port; `mock`, `deterministic` and live adapters; per-capability routing |
| Generators | `ScreenplayParser.parse` (regex), `HistoricalInvestigator.investigate` (keyword-switched fixtures), `StoryboardAligner.generate_panels` (templated), `FilmBibleSynthesizer.synthesize_rules` (6 fixed rules) | Same classes survive as the `deterministic`/`mock` adapters behind the gateway; every run is labelled with its generator mode |
| Context | Each node queries the DB ad hoc, e.g. `film_bible_synthesis/graph.py::synthesize_visual_rules` reads all scenes and claims | Context Resolver produces versioned, hashed `context_packages`; model nodes read only packages |
| Output validation | Candidates are plain `dict`s; `float(r.get("confidence", 0.9))` defaults silently | Pydantic schema per capability; typed failure; no silent defaults |
| Canon protection | AI paths write candidates only (good); manual POSTs bypass review (CODE-07 / SEC-06, G04-D) | Invariant enforced in code and tests: AI produces candidates; only review services promote |
| Graph runtime | 4 graphs; G-04 broken (G04-A…G); worker re-delivery restarts from START | Shared approval-gate subgraph, resume-from-checkpoint, idempotent propose |
| Evaluation | None | Golden sets, rubrics and metrics per capability; `evaluation_records`; release gates |
| Cost / observability | None | `ai_runs`, `usage_records`, budgets, redacted traces |

---

## 2. Layered architecture

```mermaid
flowchart TB
  subgraph API["apps/api routers"]
    R1["POST /workflows/... start"]
    R2["POST /approvals/{id}/decision"]
  end
  subgraph SVC["packages/services - application services"]
    RS["*Service.start / execute / decide"]
    REV["*ReviewService propose / commit / reject - ONLY canonical writer"]
    CR["ContextResolver - deterministic"]
    PC["PromptCompiler - WF-09"]
  end
  subgraph WF["packages/workflows - LangGraph graphs"]
    G["WF-nn StateGraph"]
    AG["approval_gate subgraph - shared"]
  end
  subgraph AI["packages/ai - new"]
    MG["ModelGateway port"]
    RT["ModelRouter"]
    PV["PromptRegistry - prompt_versions"]
    SO["StructuredOutput validator - Pydantic"]
    GR["Guardrails - input isolation, tool allowlist"]
  end
  subgraph AD["adapters"]
    M["MockAdapter - label mock"]
    D["DeterministicAdapter - label deterministic"]
    L["Live adapters - per DEC-004"]
  end
  PG[("PostgreSQL - canonical tables, context_packages, ai_runs, evaluation_records, checkpoints")]

  R1 --> RS --> G
  R2 --> RS
  G --> CR --> PG
  G --> MG
  MG --> RT --> M & D & L
  MG --> PV
  MG --> SO
  MG --> GR
  G --> REV --> PG
  G --> AG
  PC --> CR
```

New code goes in a new package, `packages/ai/` (gateway, router, prompts, structured-output schemas, guardrails, eval harness). The ADR-001 layering is unchanged. Routers call services, services start graphs, graph nodes orchestrate, and review services own every canonical write. The Addendum §5.2 rule stands: no canonical mutation without a domain-service command.

---

## 3. LLM layer: the `ModelGateway` port

### 3.1 Contract

A single, provider-neutral, **structured-output-first** port. Graph nodes and services never import a provider SDK.

```python
# packages/ai/gateway.py  (TARGET — illustrative signature, not implemented)
class ModelRequest(BaseModel):
    capability: CapabilityId              # e.g. "script.extract_scenes", "research.extract_claims"
    prompt_version_id: str                # FK prompt_versions
    context_package_id: str               # FK context_packages (hash-verified before call)
    untrusted_inputs: list[UntrustedBlock]  # uploaded-document text, isolated (see §10)
    output_schema: type[BaseModel]        # Pydantic model; JSON Schema sent where supported
    max_output_tokens: int
    budget_ref: BudgetRef                 # org/project budget to debit (see §12)
    idempotency_key: str                  # = hash(run_id, node, attempt, package_hash, prompt_version)

class ModelResult(BaseModel):
    ai_run_id: str
    generator_mode: Literal["deterministic", "mock", "live"]
    model_ref: str | None                 # "live:<provider>/<model>@<version>" — None for deterministic
    parsed: BaseModel | None              # validated instance
    validation: ValidationOutcome         # ok | repaired | failed(errors)
    usage: Usage                          # tokens, latency_ms, cost_estimate (live only)

class ModelGateway(Protocol):
    def generate(self, req: ModelRequest) -> ModelResult: ...
```

The gateway (1) verifies the context package hash, (2) resolves the route (§7), (3) applies guardrails (§10), (4) calls the adapter, (5) validates and at most once repairs (§9), (6) writes an `ai_runs` row and `usage_records`, and (7) returns. It never writes canonical tables.

### 3.2 Adapters

| Adapter | Label (`generator_mode`) | Purpose | Status |
|---|---|---|---|
| `DeterministicAdapter` | `deterministic` | Wraps rule-based components that are a legitimate product baseline: `ScreenplayParser` (WF-01), the `RuleConflictDetector` regexes (WF-04), ffprobe-style metadata checks (WF-11) | TARGET, wrapping existing code |
| `MockAdapter` | `mock` | Wraps fixture generators that only imitate intelligence: `HistoricalInvestigator`, `StoryboardAligner`, `FilmBibleSynthesizer`. Used in tests, demos and offline dev. **Must never be presented as AI output.** The UI shows a `MOCK` badge on every run and candidate it produced. | TARGET, wrapping existing code |
| `RecordedAdapter` | `mock` (sub-label `replay`) | Replays recorded live responses keyed by `(capability, prompt_version, package_hash)` for contract and regression tests | TARGET |
| Live adapters | `live` | One per selected LLM provider | **OPEN — DEC-004** |

**OPEN — DEC-004 (Model gateway / LLM).** Recommendation: build the port plus Deterministic, Mock and Recorded adapters first (Phase C). Then run an evaluation spike (§11) with at least two candidate providers on the WF-01 and WF-02 golden sets. Select per capability on measured accuracy, cost and latency, not brand. `config.py` gains `model_gateway_provider: Literal["mock","deterministic","live"]` and a `model_routes` mapping. The existing `openai_api_key` / `anthropic_api_key` / `gemini_api_key` fields move to the credential vault (`INTEGRATION_ARCHITECTURE.md` §7) before any live use. They are never read from `.env` in staging or production.

### 3.3 Migration of current generators (additive, expand→switch)

1. **Expand.** Add `packages/ai/` and the adapters. Each existing generator becomes a callable adapter target with an unchanged signature.
2. **Switch.** Graph nodes call `gateway.generate(...)`, e.g. `historical_research/graph.py`'s investigate node and `storyboard_intelligence/graph.py::generate_panels_node`. The output is the same candidate dicts, now as validated Pydantic objects, plus `ai_run_id` and `generator_mode`.
3. **Label.** Candidate tables gain `ai_run_id` (nullable, backfilled `NULL` = "pre-gateway, deterministic/mock") and the API exposes `generator_mode`. This closes audit 06 recommendation 7.
4. **Contract.** No removal. The fixture classes remain permanently as the Mock adapter.

---

## 4. Context Resolver

### 4.1 Responsibility

The Context Resolver is a **deterministic application service** (`packages/services/context_resolver.py`, *not* a graph and *not* an LLM). Given a request scope, it selects the canonical facts a model or a prompt compiler may see, records what it excluded and why, and freezes the result as an immutable, content-hashed `context_packages` row.

Model nodes receive **only** a `context_package_id` (and the isolated untrusted blocks, see §10). They never query canonical tables directly. This replaces today's ad hoc reads, e.g. `synthesize_visual_rules` loading every scene and every claim, and the claim-by-statement matching in `FilmBibleReviewService.commit_approved_candidates`.

### 4.2 Inputs → package

| Input | Example |
|---|---|
| `purpose` | `wf03.storyboard_panels`, `wf06.shot_candidates`, `wf09.compile_shot`, `wf08.director_review` |
| `scope` | project + `screenplay_version_id` + optional sequence/scene/shot/character IDs |
| `pinned_version` | `projects.current_version` at run start (`workflow_runs.expected_project_version`) |
| `policy` | per-purpose inclusion rules (below), token budget, sensitivity ceiling |

Inclusion rules are declarative per purpose and live in code with a version (`resolver_version`). For example, `wf09.compile_shot` includes:
- the approved shot and `camera_spec`
- the scene
- the character version and current `character_states` at that shot
- costume/prop/environment states
- the Film Bible rules in force (`strictness` ≥ guideline)
- the cinematography profile
- approved continuity decisions affecting the shot
- consent status flags (not consent documents)

It excludes candidates, rejected items, superseded versions, AI suggestions not accepted into `screenplay_versions`, and any `restricted_identity` asset content unless consent allows the purpose (see `CHARACTER_AND_DIGITAL_HUMAN_ARCHITECTURE.md` §6).

### 4.3 Package format and hashing

```json
{
  "package_schema": "tattva.context_package/1",
  "resolver_version": "1.0.0",
  "purpose": "wf09.compile_shot",
  "project_id": "…", "organization_id": "…",
  "project_version": 42, "screenplay_version_id": "…",
  "items": [
    {"kind": "scene", "id": "…", "version": 42, "fields": {"heading": "EXT. DHAULI HILL - DAWN", "summary": "…"}},
    {"kind": "film_bible_rule", "id": "…", "version": 40, "fields": {"title": "…", "rule_text": "…", "strictness": "mandatory"}},
    {"kind": "claim", "id": "…", "version": 37, "fields": {"statement": "…", "claim_class": "historical_fact", "source_tier": "tier_1_primary"}}
  ],
  "exclusions": [
    {"kind": "film_bible_rule_candidate", "id": "…", "reason": "not_approved"},
    {"kind": "asset", "id": "…", "reason": "consent_scope_missing:likeness_image"}
  ],
  "budget": {"max_tokens": 12000, "estimated_tokens": 8310, "truncated": false}
}
```

- **Hash.** `package_hash = sha256(canonical_json(package))`. Canonical JSON uses sorted keys, UTF-8, no insignificant whitespace, and items sorted by `(kind, id)`. Timestamps and row UUIDs of the package itself are excluded from the hashed body.
- **Versioning.** Packages are immutable. A new canonical version means a new package. `(project_id, purpose, scope_key, package_hash)` is unique, so identical resolution reuses the row (dedupe).
- **Determinism test.** Resolving twice at the same `project_version` must yield the identical hash. This is a required unit test per purpose.
- **Budget overflow.** The resolver never silently truncates. It applies the per-purpose priority order (mandatory rules > approved states > scene text > claims by tier) and records `truncated: true` with the dropped item IDs in `exclusions` (reason `budget`).
- **Traceability.** `ai_runs.context_package_id`, `production_packages.context_package_id` and `prompt_versions` together answer "what did the model see, under which instructions" for any candidate or package (Gap Report §9: "Store model route, prompt/compiler version, source refs, exclusion refs").

Table `context_packages` columns are owned by `DATABASE_DESIGN_AND_ERD.md`. Minimum needs: `id`, `organization_id`, `project_id`, `purpose`, `scope_key`, `project_version`, `resolver_version`, `package_hash`, `body` (JSONB), `excluded` (JSONB), `created_at`, `created_by_run_id`.

---

## 5. Project memory

- **The canonical tables are the memory.** There are no per-agent memories, scratchpads or vector "memories" that survive a run. This is already the principle in the code, since every graph re-reads canon via repositories. The target formalises it through the Context Resolver.
- **LangGraph checkpoints are execution state, not memory** (Addendum §5.2). They hold references and compact candidate data (`ScriptIntelligenceState` docstring) and are pruned per retention policy (DEC-007).
- **`ai_runs` is a log, not memory.** Prior model outputs reach later runs only after a human promotes them to canon, e.g. an approved research claim that the resolver then includes.
- **Human decisions are memory.** `creative_decisions`, `continuity_decisions` and approval notes are canonical and resolvable, which is how "the director already said no to X" reaches future runs.

---

## 6. RAG and pgvector: only when justified

**CURRENT:** the pgvector image is used (`docker-compose.yml`), but there are no embeddings or vector columns. That is correct.

**Rule:** a retrieval index is introduced for a purpose only when **all** of the following hold:
1. The candidate canonical set for that purpose regularly exceeds the context budget after structured filtering by scope, version and entity links.
2. A golden-set evaluation shows retrieval beats structured selection on that purpose's metric (§11).
3. The index is **derived**: rebuildable from canonical rows and assets, carries `organization_id`/`project_id`, and every query is filtered by them before similarity ranking (permission-filtered).
4. Retrieved chunks pass through the Context Resolver and are recorded in the package like any other item, with `kind: "excerpt"` and a source locator.

Likely first justified purposes, all FD-V2 and evaluation-gated:

| Purpose | Why structured selection may not suffice |
|---|---|
| WF-02 research over large uploaded source documents | Source text far exceeds context; claims need locator-precise excerpts |
| WF-08 AI Director review across a long screenplay | Cross-scene recall of motifs or contradictions |
| Long-tail continuity lookups (WF-07) | "Has this prop appeared damaged before?" across hundreds of shots, where structured `prop_states` do not already answer it |

Embeddings never become canonical truth (Gap Report §9). The derived-index table and the embedding model choice are **OPEN — DEC-016** (new; see §15).

---

## 7. LangGraph usage

### 7.1 Graph vs plain service per workflow

Per Addendum §5.1/§5.2: use a graph when work is multi-step with branching, pauses for humans, or must survive restarts. Otherwise use a plain service.

| WF | Name (legacy alias) | Runtime | Rationale |
|---|---|---|---|
| WF-01 | Script Intelligence (G-01) | **Graph** (exists) | Extract → candidates → human gate → commit |
| WF-02 | Historical Research (G-02) | **Graph** (exists) | Multi-step retrieval/extraction, conflicts, human gate |
| WF-03 | Storyboard Intelligence (G-03) | **Graph** (exists) | Panel ingestion and mapping, human gate. FD-V1 adds an image/PDF panel-ingestion branch (CODE-05) |
| WF-04 | Film Bible Synthesis (G-04) | **Graph** (WIP, broken) | Synthesis → conflict check → human gate |
| WF-05 | Character & Asset Intelligence | **Graph** | Candidate characters/costumes/props/locations from canon + references; human gate |
| WF-06 | Shot Planning | **Graph** | Scene → shot candidates with `camera_spec` recommendations; director override gate |
| WF-07 | Continuity Validation | **Service + optional graph node** | Deterministic rule checks are a plain service (`ContinuityService.check`). The AI-assisted comparison (FD-V2) is a graph only when it needs a human gate |
| WF-08 | AI Director Review | **Graph** | Aggregates findings; human accepts or dismisses each; never auto-applies |
| WF-09 | Prompt Compilation | **Plain service** (`PromptCompiler`) | Deterministic transform Shot Spec → provider package (§8). Called by WF-10 and by "export manually" |
| WF-10 | External Handoff | **Graph** | Readiness → consent/cost gates (interrupts) → submit/export → poll → import. Long-lived, must survive restarts |
| WF-11 | Output Inspection | **Graph** | Import → deterministic checks → AI comparison (FD-V2) → human review → revision request |
| WF-12 | Capture Planning (new) | **Plain service** | Rule-driven instruction generation (`HYBRID_PRODUCTION_AND_CHROMA_WORKFLOW.md` §3) |
| WF-13 | Footage Ingestion & Analysis (new) | **Graph** | Probe → per-check fan-out → findings → human triage |
| WF-14 | Screenplay Change Impact (new) | **Service** for impact analysis; approval via generalized `approval_requests` | Deterministic diff and dependency walk; no model required in V1 |
| WF-15 | Screenplay Suggestions (new; proposed by PRD v1.0) | **Graph** | Writes AI rewrite suggestions to `screenplay_suggestions` (Suggestions Workspace) only; never touches the locked `screenplay_versions` |

Simple CRUD stays in services, e.g. rule edits, profile saves and registry entries. Per CODE-07, **manual creation of canon must also go through a proposal + approval** (or an explicit "direct canon edit" capability with an audit reason), never a raw insert.

### 7.2 Current inconsistencies and fixes

| # | Inconsistency (evidence) | Fix |
|---|---|---|
| L1 | **Re-delivery restarts from START.** `ScriptIntelligenceService.execute` (and the same pattern in the three sibling services) always calls `_invoke(run.id, initial_state)`. If a worker crashes after `generate_candidates_node` committed, the outbox re-delivers, `parse` runs again and a **second** set of candidates and a second `approval_requests` row are written. | `execute()` first reads `graph.get_state(config)`. If a checkpoint exists with `next` non-empty, call `graph.invoke(None, config)` to resume. If the state is parked at the approval interrupt, return without invoking (the decision path resumes it). Only with no checkpoint does it start with `initial_state`. |
| L2 | **Propose is not idempotent.** `*ReviewService.propose*` always inserts. | Before inserting, look up an existing approval request for `(workflow_run_id, scope)`. If one exists, return it (idempotent). Add a partial unique index `approval_requests(workflow_run_id, scope) WHERE status='pending'` (DB doc owns). |
| L3 | **G-04 state undeclared keys (G04-A).** `FilmBibleState` lacks `approved_rule_ids`, `decision_notes`, `decided_by`, so LangGraph drops them and partial approval commits all rules. | Declare them. Add a test asserting that a partial approval commits exactly the subset. |
| L4 | **G-04 overloads `actor_id` and `expected_project_version`.** `human_approval_gate` overwrites `actor_id` with the decider. `commit_rules` writes the *new* version into `expected_project_version`. | Use `decided_by` like WF-01…03. Return `new_project_version`. Never mutate the start-time expectation. |
| L5 | **G-04 gate lacks the pending guard and raises `TypeError` on non-dict resume (G04-G).** | Replace all four hand-written gates with one shared `approval_gate` subgraph (§7.3). |
| L6 | **G-04 calls a non-existent repo method (G04-B)** `ResearchRepository.list_claims_for_project`. | Use the Context Resolver (`purpose=wf04.film_bible`), which reads claims through the existing `list_claims`. |
| L7 | **Checkpointer `setup()` on every invoke** (`packages/workflows/checkpointer.py`). | Run `setup()` once at startup or migration (a CLI step next to Alembic). `get_checkpointer()` only opens. |
| L8 | **Graph version not used for resume safety.** `workflow_runs.graph_version` defaults to `"1.0"`. Changing a graph's node set can break resume of old threads. | Bump `*_GRAPH_VERSION` on any topology change. The resume path refuses to resume a thread whose `graph_version` differs from code unless a migration shim is registered. Old runs are then marked `superseded_by_upgrade` and can be restarted by the user. |
| L9 | **Sync by default** (`schemas.py sync_execution=True`, CODE-04). | Default `False`. Sync allowed only in `environment=test`. |
| L10 | **Interrupt payloads differ** (`message` vs `type`). | Shared gate emits `{"type": "approval_required", "approval_request_id", "scope", "candidate_count"}`. |
| L11 | **Rejection version semantics differ.** Storyboard `reject_candidates` returns `current_version`; script `close_rejected` returns `None`. | Standardise: rejection never bumps the version and returns `None`. Result reports `new_project_version=None`. |

### 7.3 Shared approval-gate subgraph

There are four copies of the same gate today, which justifies the abstraction. Signature: `build_approval_gate(scope: str, selection_keys: list[str])`. It returns a compiled subgraph that:
1. returns `{}` when `approval_status != "pending"` (replay-safe)
2. calls `interrupt()` with the standard payload
3. coerces non-dict resumes to a rejection with `decision_notes="invalid_resume_payload"` (never raises)
4. maps `selection_keys`, e.g. `approved_rule_ids`, with `None` meaning all and `[]` meaning none, matching the current WF-01 convention.

The canonical decision is already persisted before resume by `*Service.decide` (invariant 4). That stays.

```mermaid
stateDiagram-v2
  [*] --> queued: start - outbox row
  queued --> running: worker claims - lease
  running --> awaiting_approval: propose committed - interrupt
  running --> failed: typed failure
  running --> running: re-delivery - resume from checkpoint L1
  awaiting_approval --> committing: decide persisted - Command resume
  committing --> completed: review service commit + version bump
  awaiting_approval --> rejected: decide rejected
  committing --> failed: version conflict - no auto retry
  failed --> queued: user retry - new attempt same run if checkpoint valid
  completed --> [*]
  rejected --> [*]
```

Worker lease, retry and dead-letter semantics (`outbox_tasks` extensions) are specified in the engineering/ops documents. This document only requires that a retry **resumes** and never restarts a graph.

---

## 8. Prompt compiler (WF-09)

**Purpose:** turn an approved, provider-neutral **Shot Spec** into a provider-specific (or manual-target) **production package** with no loss of provenance. It is deterministic. An LLM may be used only in an *optional* "prose rendering" step whose output is itself validated and diffed against the deterministic rendering.

```mermaid
flowchart LR
  A["Approved shot + camera_spec + references"] --> B["ContextResolver purpose wf09.compile_shot"]
  B --> C["Normalize to ShotSpec v1 - Pydantic"]
  C --> D{"Target"}
  D -- connected --> E["Load provider_capability_snapshots row - pinned id"]
  D -- manual --> F["Load manual target profile - registry"]
  E --> G["Capability check: each field supported / translatable / unsupported"]
  F --> G
  G --> H["Render: structured params + prompt text + negative guidance + reference manifest"]
  H --> I["Validate against snapshot input schema"]
  I --> J["production_packages row - package_hash, compiler_version, snapshot_id, context_package_id"]
  G -- "unsupported mandatory field" --> X["Block with explanation - user picks other tool or relaxes"]
```

- **Field disposition** is per Shot Spec field against the snapshot (detail in `CINEMATOGRAPHY_AND_VIRTUAL_CAMERA_ARCHITECTURE.md` §6):
  - `native` maps to a declared provider parameter
  - `prompt_text` is rendered into the prompt using a versioned phrase template
  - `reference` is satisfied by a reference asset role
  - `unsupported` is dropped with a warning, or **blocks** if the Film Bible or director marked it mandatory.
- **Every compiled package records** `compiler_version`, `prompt_version_id` (templates), `provider_capability_snapshot_id` (or manual target), `context_package_id`, `package_hash` and the disposition table. This lets a reviewer see exactly what the provider was told and what was lost.
- **Film Bible rules** with `negative_prompt_guidance` render into a negative prompt only if the snapshot declares negative-prompt support. Otherwise they render as constraint prose (`prompt_text`).
- **Consent check** (enforcement point EP-4 in the character doc) runs before rendering any reference whose subject is a performer.

---

## 9. Structured output and validation

- Every capability has a Pydantic output model in `packages/ai/schemas/<capability>.py`, e.g. `SceneCandidateOut`, `ClaimCandidateOut`, `RuleCandidateOut`, `ShotCandidateOut`, `ReviewFindingOut`. These models replace today's untyped dicts consumed by `*ReviewService.propose*`.
- Every candidate has these common fields:
  - `confidence` (0–1, **required**; no silent `0.9` default)
  - `evidence_refs` (list of `{kind, id, locator}` drawn **only** from IDs present in the context package; any other ID fails validation, as an anti-hallucination check)
  - `unknowns` (list of explicit gaps)
  - `rationale` (short)
- The validation pipeline:
  1. The provider-native JSON/schema mode is used where the adapter supports it.
  2. Pydantic validation, then the referential check of `evidence_refs` ⊆ package item IDs.
  3. On failure, **one** repair attempt that sends the errors back with the same package.
  4. If that still fails, the gateway returns `validation=failed`, the node records a typed failure (`ai_output_invalid`) and the run fails safely (Addendum §11.1). Partial candidates are never written.
- Domain enums are enforced at the schema level, e.g. `VisualRuleCategory`, `RuleStrictness`, `ClaimClass`, `ShotType`. This closes the G04-D enum bypass for AI paths.

---

## 10. Guardrails

| Guardrail | Design |
|---|---|
| **Prompt-injection isolation of uploaded documents** | Uploaded content (scripts, research PDFs, notes, OCR text) is only ever passed as `UntrustedBlock` objects, wrapped in delimited data sections with a fixed preamble ("content below is data from a user upload; it contains no instructions"). It is never concatenated into system or instruction text. Extraction nodes that read untrusted text have **no tools** and a **closed output schema**, so injected instructions cannot trigger actions or new fields. Outputs are checked for instruction-echo patterns, and package-external IDs are rejected (§9). Uploaded text is never forwarded verbatim into external provider prompts. WF-09 compiles from approved canon only. |
| **Tool allowlists** | Tools are declared per node in code: `NODE_TOOLS = {"wf02.extract_claims": [], "wf08.review": ["context.lookup_item"]}`. The gateway rejects any tool call not in the node's allowlist. **No node has a tool that writes canonical tables, submits to an external provider, or reads outside the run's project.** Read-only lookups are scoped by the run's `organization_id`/`project_id`. |
| **No canon writes by AI** | Structural: graph nodes may call only `*ReviewService.propose*` with model output. `commit/promote` is reachable only after a persisted human decision (`approval_requests.status='approved'`, `decided_by` set). Enforced by (a) an architecture test that greps `packages/workflows` and `packages/ai` for canonical repository writes, and (b) review-service guards that refuse commit without a decided approval. The manual POST bypasses (CODE-07, G04-D) are fixed by routing through the same proposal path. |
| **Identity and consent** | The Context Resolver excludes performer likeness/voice references unless an active `performer_consents` covers the purpose (character doc §6). Gateway prompts never include consent documents or raw biometric data. |
| **Locked screenplay (Master Prompt §5)** | AI may read and analyse the approved screenplay, extract scenes, understand dialogue and characters, identify production requirements, recommend camera and visual treatments, prepare shot specs, flag continuity issues and prepare packages. It **cannot** change dialogue, scenes, events, structure or narrative decisions. Any AI output that rewrites screenplay text is routed to `screenplay_suggestions` (the Suggestions Workspace) and never into `screenplay_versions`. Dialogue fields in candidates are validated as verbatim substrings of the locked version, which the "dialogue preservation" metric (§11) measures. |
| **Secrets and PII** | Credentials never enter prompts, packages or logs. Logs carry IDs, not script text (Addendum §11.2). |
| **Output safety for external use** | Compiled prompts pass a provider-policy lint, a list maintained per provider in the registry (e.g. Midjourney manual-target warnings, Gap Report §7.2). Only lints confirmed from provider terms are included. |

---

## 11. Evaluation framework (Master Prompt §22)

No AI capability may be labelled better than `deterministic`/`mock` in the UI or release notes without a passing evaluation record on its golden set.

### 11.1 Per-capability matrix

| Capability | Golden set (minimum to start) | Rubric / labels | Metrics | Gate (initial proposal) |
|---|---|---|---|---|
| WF-01 scene and entity extraction | 30 screenplays across formats: clean Fountain-like, non-uppercase cues, PDF-extracted, Indian multilingual headings; hand-labelled scenes/characters/locations with line locators | Exact/partial match per scene boundary and entity | Scene boundary F1, entity F1, locator accuracy | ≥ current regex baseline on all; ≥ 0.9 scene F1 to claim "AI" |
| WF-02 claim extraction and citation | 50 source excerpts with labelled claims, class (`ClaimClass`), tier, locator | Historian rubric: faithful / unsupported / misattributed | Claim precision, citation-locator precision, unsupported-claim rate | Unsupported-claim rate ≤ 2%; any fabricated citation is a release blocker |
| WF-02 conflict surfacing | 20 claim pairs with known disagreements | Detected / missed | Conflict recall | ≥ 0.8 |
| WF-03 panel↔scene mapping | 15 storyboards (image/PDF) with labelled panel→scene | Correct / adjacent / wrong | Mapping accuracy | ≥ 0.85 |
| WF-04 rule synthesis | 10 projects with director-approved bibles | Director rubric 1–5: relevance, specificity, historical consistency | Mean score, contradiction rate vs canon claims | Mean ≥ 3.5, contradictions = 0 unflagged |
| WF-05 character/asset candidates | 10 scripts with labelled character lists, costume/prop mentions | Match / missing / spurious | Recall, spurious rate | Recall ≥ 0.9 |
| WF-06 shot candidates and camera recommendations | 20 scenes with DP-authored shot lists | DP rubric: coverage, intent fit, explanation quality | Coverage %, mean rubric | Mean ≥ 3.5 |
| WF-07 continuity detection | 25 sequences with seeded continuity breaks (costume, prop, injury, time-of-day) | Detected / missed / false alarm | Recall, precision | Recall ≥ 0.85 for deterministic rules (exact); AI-assisted reported separately |
| WF-08 director review | 10 scripts with expert notes | Useful / redundant / wrong | Useful-finding rate, wrong-finding rate | Wrong ≤ 10% |
| WF-09 prompt compilation | 40 Shot Specs × each registered target | Field disposition correctness, no lost mandatory fields | Disposition accuracy, mandatory-field loss = 0 | Deterministic; must be 100% |
| WF-11 output inspection | Provider outputs with labelled deviations | Detected / missed | Recall | Reported only (FD-V2) |

Thresholds are **proposals for the approval gate** and are recorded per capability in the evaluation config. They are not claims about any model.

### 11.1a Master Prompt §22 metric coverage

Every §22 metric has a named metric key (stored in `evaluation_records.metrics`), a capability that owns it, and a method. A metric marked *human* uses the rubric raters. *auto* is computed against labels.

| §22 family | Metric (verbatim) | Metric key | Owning capability | Method |
|---|---|---|---|---|
| Story | scene extraction accuracy | `story.scene_extraction_f1` | WF-01 | auto: scene boundary F1 vs labels |
| Story | character extraction accuracy | `story.character_extraction_f1` | WF-01 / WF-05 | auto: entity F1 incl. alias merge |
| Story | dialogue preservation | `story.dialogue_preservation_rate` | WF-01, WF-06, WF-09 | auto: % dialogue in candidates/packages that is byte-identical to the locked `screenplay_versions` text (target 100%) |
| Story | script source traceability | `story.locator_accuracy` | WF-01 | auto: % candidates whose locator resolves to the correct source line |
| Story | screenplay version correctness | `story.version_binding_correctness` | WF-01, WF-06, WF-09 | auto: % shots/packages bound to the approved-for-production `screenplay_version_id` at creation (target 100%) |
| Research | source coverage | `research.source_coverage` | WF-02 | auto: % labelled relevant sources cited at least once |
| Research | evidence traceability | `research.citation_locator_precision` | WF-02 | auto: % claims with a locator that contains the claim |
| Research | factual reliability | `research.unsupported_claim_rate` | WF-02 | human (historian rubric) |
| Research | conflict identification | `research.conflict_recall` | WF-02 | auto vs labelled conflicts |
| Research | confidence calibration | `research.calibration_ece` | WF-02 | auto: expected calibration error of `confidence` vs rater-judged correctness |
| Character | identity consistency | `character.identity_consistency` | WF-05, WF-11 | human side-by-side vs approved identity references (DEC-017: no biometric automation) |
| Character | face-reference adherence | `character.face_reference_adherence` | WF-11 | human rubric 1–5 |
| Character | body proportion consistency | `character.body_proportion_consistency` | WF-11 | human rubric vs `physical_identity_profiles` |
| Character | costume consistency | `character.costume_consistency` | WF-07, WF-11 | human rubric vs effective `costume_states` |
| Character | avatar quality | `character.avatar_quality` | WF-05 (digital-human review) | human rubric |
| Cinematography | shot suitability | `cin.shot_suitability` | WF-06 | human DP rubric |
| Cinematography | camera recommendation quality | `cin.camera_rec_quality` | WF-06 | human rubric + override rate |
| Cinematography | lens recommendation quality | `cin.lens_rec_quality` | WF-06 | human rubric + override rate |
| Cinematography | visual intent alignment | `cin.visual_intent_alignment` | WF-06, WF-08 | human rubric vs director intent / bible |
| Cinematography | technical parameter validity | `cin.parameter_validity` | WF-06 | auto: % specs passing schema, lens set and format checks (target 100%) |
| Package | prompt completeness | `pkg.prompt_completeness` | WF-09 | auto: % mandatory spec fields present in rendered output or dispositioned |
| Package | reference coverage | `pkg.reference_coverage` | WF-09 | auto: % required reference roles attached |
| Package | correct provider mapping | `pkg.mapping_accuracy` | WF-09 | auto vs golden disposition tables |
| Package | parameter validation | `pkg.parameter_validation_pass` | WF-09 | auto: payload validates against the snapshot schema |
| Package | manual handoff completeness | `pkg.manual_handoff_completeness` | WF-09 / manual adapter | auto checklist (prompt, settings, references, checksums, instructions) + human usability rating |
| Output inspection | character consistency | `out.character_consistency` | WF-11 | human |
| Output inspection | motion quality | `out.motion_quality` | WF-11 | human |
| Output inspection | lighting consistency | `out.lighting_consistency` | WF-11 | human (HEUR assist, FD-V2) |
| Output inspection | framing | `out.framing_match` | WF-11 | human + auto aspect/resolution checks |
| Output inspection | lip-sync | `out.lip_sync` | WF-11 | human rubric (automated metric only after an evaluation set exists) |
| Output inspection | visual artifacts | `out.artifact_rate` | WF-11 | human-labelled |
| Output inspection | continuity detection precision & recall | `out.continuity_precision`, `out.continuity_recall` | WF-07 / WF-11 | auto vs seeded continuity breaks |

**§22 tracking.** Each evaluated item and each production AI run records the following (on `ai_runs`, `evaluation_records` and `output_reviews`):

| §22 tracked item | Where |
|---|---|
| prompt version | `prompt_version_id` |
| model version | `model_ref` (`live:<provider>/<model>@<version>`) |
| provider version | `provider_capability_snapshot_id` (external) or adapter version (LLM) |
| input asset version | `context_package_id` (item versions) + package `reference manifest` asset versions |
| output asset version | output `asset_id` + version |
| human review | `approval_requests` / `output_reviews` decision, reviewer |
| correction | edited fields diff between AI candidate and committed canon (stored on the review) |
| final acceptance | `final_accepted` flag + timestamp when the item becomes approved canon or the selected output |

### 11.2 Mechanics

- **Harness:** `packages/ai/eval/` with `evals/<capability>/` datasets (versioned and checksummed; containing no customer data without written permission). Runner command: `python -m packages.ai.eval run <capability> --route <route>`.
- **Records:** each run writes `evaluation_records` with `capability`, `dataset_version`, `prompt_version_id`, `model_ref`/`generator_mode`, metrics JSON, rubric scores, rater IDs (for human-rated items), `passed`, and `created_at`.
- **When it runs:**
  - The deterministic and mock adapters run in CI on every PR (cheap, catches regressions in parsers and the compiler).
  - Live routes run on prompt or route change and nightly with a budget cap.
  - Human-rubric evaluation is run before each release label (FD-V1/FD-V2).
- **Online signal:** reviewer decisions are labelled feedback. Each review counts approval, partial approval or rejection of AI candidates per capability, and `ai_run_id` links each decision to the run that produced the candidate. These counts are tracked, but they never retrain anything automatically.

---

## 12. Model routing and cost controls

- **Routing.** `model_routes` maps `capability → [primary route, fallback route]`, e.g. `research.extract_claims → [live:A/model-x, live:B/model-y]`. Routes are per environment and optionally per organization, since an org may forbid a provider for data-residency reasons. A route change creates a new route version and requires a passing evaluation record (§11) before it becomes primary.
- **Fallback.** Use the fallback route on a retryable provider error only (rate limit, 5xx, timeout), never on a validation failure. If all routes fail, the run fails. **Live capabilities never silently fall back to `mock`.**
- **Budgets.** Org and project monthly budgets live in `usage_records`, aggregated per org and project. The gateway pre-estimates the cost from package token estimates. When the projected spend would exceed the budget, the call is refused with `budget_exceeded`. Thresholds trigger `notifications` at 50%, 80% and 100%.
- **Caching.** Identical `(capability, prompt_version_id, package_hash, model_ref)` requests reuse the stored result (cache hit recorded in `ai_runs`). This makes re-runs on unchanged canon cheap and reproducible.
- **Limits.** Each capability has a ceiling on max input tokens (enforced by the resolver budget) and on max output tokens.

---

## 13. AI observability

For every gateway call, an `ai_runs` row records:
- run, node and attempt
- capability
- `generator_mode` and `model_ref`
- `prompt_version_id` and `context_package_id`
- latency
- input/output token counts
- cost estimate
- validation outcome
- repair attempted
- cache hit
- error class
- trace ID

Prompt and response bodies are stored **only** in object storage under the project's retention policy (DEC-007), referenced by ID. They are never written to ordinary logs or third-party tracing until a redaction policy is approved (Addendum §11.2).

Initial dashboards cover:
- runs by capability and mode
- validation-failure rate
- repair rate
- p95 latency
- spend by org and project
- reviewer acceptance rate per capability
- evaluation trend per route

---

## 14. Requirements introduced (for the traceability matrix)

| ID | Requirement | Release |
|---|---|---|
| TFD-AID-001 | All model access goes through `ModelGateway`; no provider SDK import outside `packages/ai/adapters` | FD-V1 |
| TFD-AID-002 | Every run and candidate exposes `generator_mode` (`deterministic`/`mock`/`live`); the UI badges mock output | FD-V1 |
| TFD-AID-003 | AI output is validated against a Pydantic schema; evidence refs must exist in the context package | FD-V1 |
| TFD-AID-004 | AI never writes canonical tables; enforced by architecture test | FD-V1 |
| TFD-AID-005 | Uploaded content is passed only as isolated untrusted blocks; extraction nodes have no tools | FD-V1 |
| TFD-AID-006 | Golden set + `evaluation_records` required before a capability is labelled live | FD-V1 (WF-01/02), FD-V2 (others) |
| TFD-AID-007 | Org/project AI budgets with pre-call refusal | FD-V1 before first live route |
| TFD-CTX-001 | Context Resolver produces immutable, hashed, versioned `context_packages`; resolution is deterministic | FD-V1 |
| TFD-CTX-002 | Packages record exclusions with reasons, including budget truncation | FD-V1 |
| TFD-OPS-0xx | Worker re-delivery resumes from checkpoint; propose is idempotent (L1, L2) | FD-V1 (Phase C) |

---

## 15. Open decisions

| ID | Decision | Recommendation |
|---|---|---|
| **OPEN — DEC-004** | LLM providers per capability | Gateway + Deterministic/Mock/Recorded adapters first; evaluation spike on WF-01/WF-02 golden sets; select per capability |
| **OPEN — DEC-007** | Retention of prompts, responses, checkpoints | Store bodies in object storage, keep 90 days by default, keep `ai_runs` metadata indefinitely; final policy by Legal |
| **OPEN — DEC-010** | G-04 fix-forward | Apply L3–L6 as part of the G04 fix; adopt the shared gate in the same change |
| **OPEN — DEC-016** (new) | Derived retrieval index: table design, embedding model, when to enable | Do not build in FD-V1. Enable per purpose only after §6 criteria pass; embedding model chosen through the DEC-004 spike |
