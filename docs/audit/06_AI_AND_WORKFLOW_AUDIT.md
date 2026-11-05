# 06 — AI and Workflow Audit

**Doc ID:** TFD-AUDIT-006 · **Audit date:** 2026-11-05

## 1. Headline
**There is no AI inference in the codebase.** Every "intelligence" component is deterministic Python: regex, keyword switches or hardcoded content. The orchestration around it (LangGraph state, interrupt and resume, approval gates, Postgres checkpointing) is real and largely sound. The intelligence itself is MOCKED or PLACEHOLDER.

## 2. Workflow inventory

| Graph | Nodes | Generator | Classification |
|---|---|---|---|
| G-01 Script Intelligence (`workflows/script_intelligence`) | parse → generate_candidates → human_approval_interrupt → route → commit / record_rejection | `ScreenplayParser.parse` (regex sluglines, uppercase cues) | Deterministic baseline; legitimately useful; VERIFIED locally |
| G-02 Historical Research (`workflows/historical_research`) | investigate → generate_candidates → interrupt → route → commit / reject | `HistoricalInvestigator.investigate`: docstring says "Deterministic … mock LLM adapter"; keyword-switched content (kalinga/maurya/ashoka) | MOCKED |
| G-03 Storyboard (`workflows/storyboard_intelligence`) | generate_panels → generate_candidates → interrupt → route → commit / reject | `StoryboardAligner.generate_panels` from text brief; lens notes hardcoded | MOCKED / PLACEHOLDER |
| G-04 Film Bible (`workflows/film_bible_synthesis`, WIP) | synthesize_visual_rules → human_approval_gate → route → commit_rules / reject_rules | `FilmBibleSynthesizer`: 6 fixed rules; `RuleConflictDetector` exact-phrase regex | BROKEN (G04-A/B), PLACEHOLDER content |

## 3. Orchestration quality

| Aspect | Finding |
|---|---|
| State | `TypedDict(total=False)` per graph. G-04 is missing `approved_rule_ids` / `decision_notes`, and LangGraph silently drops undeclared keys (G04-A) |
| Checkpointing | `PostgresSaver.from_conn_string(...)` with `setup()` on **every** invoke (`workflows/checkpointer.py`). Thread id = `workflow_run_id`. Same DB unless `checkpoint_database_url` is set |
| Human-in-the-loop | `interrupt()` + `Command(resume=…)`. The decision is persisted and committed before resume (good). G-01…03 guard on `approval_status != "pending"`; G-04 does not |
| Recovery | `tests/workflows/test_graph_recovery.py` proves interrupt → new checkpointer → resume for **G-01 only**. The worker's `execute()` restarts from START on re-delivery (duplicates) |
| Version safety | `expected_project_version` is captured at start and checked at commit via `assert_expected_version` (good). Version-bump locking is inconsistent (see `03` §7) |
| Context | No Context Resolver. Each graph reads what it needs ad hoc (e.g. G-04 reads research claims by text) |

## 4. Missing AI-system components (all NOT_IMPL)
- **Model Gateway.** DEC-004 and the Build Plan test matrix name a `ModelGateway`, but the class does not exist. `config.model_gateway_provider: Literal["mock"]`.
- **Prompt management.** No prompts, prompt versions or prompt-compiler.
- **Structured output.** Candidates are plain dicts; no Pydantic schema validation of model output.
- **Guardrails.** No prompt-injection isolation for uploaded documents, no tool allowlists. The question is moot today because no LLM exists, but it is required before one is added.
- **Evaluation.** No golden datasets, rubrics or eval runs (`tests/` has functional tests only).
- **Cost controls and AI observability.** None.
- **RAG / pgvector.** The pgvector image is used but no embeddings or vector columns exist. Correct per the "only when justified" rule.
- **Project memory.** Canonical tables are the memory (correct principle); no Context Resolver packages them.

## 5. Recommendations (feed Phase B `AI_SYSTEM_ARCHITECTURE.md`)
1. Introduce `ModelGateway` (provider-neutral, structured-output-first, with a deterministic mock adapter clearly labelled `mock`) **before** adding any real model. Route all existing generators behind it so the mocks become one adapter, not the architecture.
2. Context Resolver as a deterministic application service producing versioned, hashed `context_packages`. LLM nodes consume packages; they never query the DB freely.
3. Keep the LangGraph pattern; fix the four-graph inconsistencies by extracting a shared approval-gate helper (small, justified abstraction: four copies already exist).
4. Call checkpointer `setup()` once at startup or migration time.
5. Re-delivery must resume from the checkpoint (`invoke(None, config)` when a checkpoint exists) or be idempotent at candidate write.
6. Build golden sets per capability before claiming any quality (Master Prompt §22).
7. UI and API must label generator mode (`deterministic` / `mock` / `live:<model>`) on every run and candidate.
