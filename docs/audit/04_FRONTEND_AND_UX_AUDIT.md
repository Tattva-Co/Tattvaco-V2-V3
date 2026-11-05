# 04 — Frontend and UX Audit

**Doc ID:** TFD-AUDIT-004 · **Audit date:** 2026-11-05

## 1. Current UI (Streamlit, `apps/ui`)
- **Shell (`app.py`):** sidebar project selector (`list_projects`, `get_project`), a navigation radio, and a "New Film Project" form with 4 fixed genres. The header shows title, logline, `current_version` and status. **"Branch: main" is hardcoded.**
- **API access:** only through `TattvaApiClient` (`api_client.py`). `components.safe_call` shows errors inline. The base URL is `settings.streamlit_api_base_url`.
- **Identity:** `TattvaApiClient` supports an `actor_id`, but `app.py` never passes one. Every UI call therefore relies on the API's dev fallback actor. **The UI cannot operate against a staging or production API.**

| View | Function | API calls | Status |
|---|---|---|---|
| `overview.py` | Counts of assets, scenes and entities; project JSON | `list_assets/scenes/entities` | IMPL_NV (smoke test only) |
| `assets.py` | Upload .fountain/.txt/.pdf; list with checksum | `upload_asset`, `list_assets` | IMPL_NV |
| `script_intelligence.py` (G-01) | Run graph, raw JSON result | `run_script_intelligence` | IMPL_NV (raw JSON UX) |
| `historical_research.py` (G-02) | 5 tabs: investigate, questions, sources, claims, conflicts | research endpoints | IMPL_NV |
| `storyboard.py` (G-03) | Panels; generate from text brief | storyboard endpoints | IMPL_NV |
| `review.py` | Unified approval tray for 4 scopes; approve-selected or reject-all | `get_candidates`, `decide_approval` | IMPL_NV |
| `film_bible.py` (WIP) | Rules, synthesis, scenes, entities, versions | film-bible endpoints | BROKEN backend (G04-B) |
| `audit.py` | Audit event list | `audit_log` | IMPL_NV |

- `tests/unit/test_ui_smoke.py` renders every view against a fake API (passes). There are no browser or E2E tests.
- **All workflow triggers use `sync_execution=True`**, so the UI blocks for the whole run. There is no task tray or polling (IA "Task Centre" is absent).
- Approval decisions are made as whatever actor the API falls back to. They are **not bound to a logged-in human** (Gap Report finding still valid).

## 2. Against target IA
- IA v1.0 defines **44 screens**: 8 global (G-01…G-08) and 36 project screens (P-01…P-36). PRD v0.9 lists 26 UX-FD screens. Master Prompt §25 proposes 25 workspace groups. **8 views exist.**
- Not represented at all:
  - character, digital human, measurements, costume/props, environment and cinematography studios
  - shot planner, production method, capture planner, tool registry, handoff studio
  - execution monitor, asset library, output inspection, continuity, voice, post handoff
  - team/permissions, project settings
- **ID collision:** IA uses `G-0x` for global screens, while the Addendum and the code use `G-0x` for graphs. The UI labels "G-02" as Historical Research; the IA's G-02 is "All Projects". Resolution: DEC-011 in `10_DOCUMENT_CONFLICT_AND_DECISION_REGISTER.md`.

## 3. Streamlit suitability against Master Prompt §18 requirements

| Requirement | Streamlit fit | Note |
|---|---|---|
| Forms, tables, review trays, dashboards | Good | Current strength |
| Script editor with diff/redline | Poor | Needs a custom component |
| Storyboard board / drag-and-drop | Poor | Custom component required |
| Media preview (video scrub, A/B compare, frame overlay) | Weak | `st.video` is basic; no synchronised compare |
| Timeline (shots/sequences) | Poor | Custom component |
| Multi-user collaboration / realtime status | Poor | Rerun model; no push channel |
| Complex navigation / deep links | Weak | Multipage is workable but limited |
| Accessibility / responsive | Moderate | Limited control over semantics |

**Assessment:** Streamlit stays suitable as the **internal alpha and control surface** for V1 intelligence workflows. It is **not** a credible surface for the V2 production workspace (media compare, storyboard boards, timeline, realtime job status). The decision is ADR-002 (Phase B), and the recommendation must not be executed before approval. Whatever the frontend, the API must become the stable contract: async jobs, a status endpoint, real authentication.

## 4. UX defects to fix regardless of framework
1. Bind every action to an authenticated user and send the auth header.
2. Run workflows asynchronously and show a task status tray using `GET /workflow-runs/{id}`.
3. Render G-01 results as structured scenes and entities, not raw JSON.
4. Make loading, empty, error, recovery and approval states explicit per screen (`SCREEN_INVENTORY_AND_BEHAVIOUR.md` in Phase B).
5. Indicate mock and deterministic generators in the UI ("no fake success", OPEN_DECISIONS invariant 3). Today the UI presents hardcoded research and film-bible output as if it were real intelligence.
