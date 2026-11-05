# Tattva AI Film Director — Revised User Journeys

**Doc ID:** TFD-PRD-UJ-001 · **Version:** 1.0-draft · **Date:** 2026-11-05 · **Status:** Phase B design — pending approval

**Inputs:**
- Master Execution Prompt §4–§14, specifically the §13 sixteen-stage lifecycle
- Gap Report §8 (journeys, plus the interruption and recovery rules in §8.3)
- IA v1.0 §9 (journeys UJ-01…UJ-11)
- `PRD_v1.0.md`
- `INFORMATION_ARCHITECTURE.md`
- `SCREEN_INVENTORY_AND_BEHAVIOUR.md`

**Supersedes:** PRD v0.9 §10 (Journeys A–J) and IA v1.0 §9 (UJ-01…11) as the journey baseline. The older journeys remain valid as entry-path examples. Their concepts are mapped in §8.

**CURRENT vs TARGET:** today only fragments of stages 1–4 and 7 exist, all through deterministic or mocked generators:
- project create and text upload (`routers/projects.py`, `routers/assets.py`)
- WF-01 scene and entity extraction
- WF-02 mocked research
- WF-03 text-brief storyboard
- WF-04 (BROKEN)
- single-tier approval (`routers/approvals.py`)

Every journey below describes **TARGET** behaviour. A **CURRENT** note marks each step that has an as-built counterpart.

---

## 1. The 16-stage lifecycle

The lifecycle is **flexible, not a wizard**. Users can enter at any stage with existing scripts, references, research or footage. Each stage writes to the shared Project Intelligence Layer, so nothing is re-explained downstream.

```mermaid
flowchart TD
  S1[1 Project creation] --> S2[2 Script and creative governance]
  S2 --> S3[3 Story intelligence]
  S3 --> S4[4 Historical research]
  S3 --> S5[5 Character development]
  S4 --> S5
  S4 --> S6[6 Environment and world]
  S5 --> S7[7 Visual direction]
  S6 --> S7
  S7 --> S8[8 Scene, sequence, shot planning]
  S8 --> S9[9 Production method selection]
  S9 -->|hybrid methods| S10[10 On-set capture planning or footage ingestion]
  S9 -->|AI methods| S11[11 Production package generation]
  S10 --> S11
  S11 --> S12[12 External execution: connected or manual]
  S12 --> S13[13 Output inspection]
  S13 --> S14[14 Revision and approval]
  S14 -->|revision| S11
  S14 -->|approved| S15[15 Production asset library]
  S15 --> S16[16 Post-production handoff]
  X1([Existing screenplay]) -.-> S2
  X2([Existing references or bibles]) -.-> S5
  X3([Existing footage]) -.-> S10
  X4([Existing research]) -.-> S4
```

| Stage | Master §13 content | Screens | Key requirements | Release |
|---|---|---|---|---|
| 1 | Format, genre, mode, quality profile, scale, team, delivery | S-GLB-02, S-PRJ-02, S-TEAM-02 | TFD-PRJ-001/003, TFD-FMT-001 | FD-V1 |
| 2 | Import or create; identify approved version; lock; suggestions apart | S-SCR-01/03/04 | TFD-SCR-001…008 | FD-V1 |
| 3 | Narrative, scenes, characters, dialogue, sequences, historical needs, story timeline, relationships | S-SCR-02, S-BRN-01/02 | TFD-STY-001…006 | FD-V1 |
| 4 | Events, evidence, sources, timeline, architecture, geography, costume, weapons, culture; fact ≠ interpretation ≠ dramatisation | S-RES-01…05 | TFD-RES-* | FD-V1 |
| 5 | Identity, profile, face, physical, measurements, costume, props, movement, performance, voice, timeline state | S-CHR-01/02, S-PHY-01, S-DH-01, S-CST-01/02 | TFD-CHR-*, PHY-*, CNS-*, CST-*, PRP-* | FD-V1 |
| 6 | Locations, architecture, interiors/exteriors, geography, terrain, weather, lighting, materials, background, accuracy, continuity | S-ENV-01 | TFD-ENV-* | FD-V1 |
| 7 | Film Bible, Visual Language, Cinematography Bible, camera/lens library, lighting, colour, references | S-BIB-01/02, S-CIN-01 | TFD-CIN-005/010…013 | FD-V1 |
| 8 | Intention, sequence, shot list, composition, lens, movement, duration, states, references, method | S-SEQ-01/02, S-SHT-01, S-SB-01/02 | TFD-SEQ-*, SHT-*, CIN-001…004 | FD-V1 |
| 9 | Fully AI / live-action chroma / transformation / digital human / combined, per shot | S-MTH-01, S-SHT-01 | TFD-SHT-002, PRJ-004/005 | FD-V1 |
| 10 | Capture requirements, or independent footage ingestion | S-CAP-01/02 | TFD-HYB-* | FD-V2 |
| 11 | Provider-neutral Shot Spec and model-specific package | S-PKG-01…03 | TFD-SHT-003, PKG-* | FD-V1 |
| 12 | Connected or manual | S-PKG-03, S-EXE-01 | TFD-INT-*, GEN-* | FD-V1 manual; FD-V2 connected |
| 13 | Identity, face, body, movement, costume, environment, lighting, composition, camera, lip-sync, artifacts, continuity, quality | S-EXE-02, S-OUT-01, S-CON-01 | TFD-OUT-001/002, CON-007 | FD-V1 human; FD-V2 AI-assisted |
| 14 | Findings; accept, reject or request change; track revisions | S-OUT-01, S-APR-02 | TFD-OUT-004/005 | FD-V1 |
| 15 | Images, keyframes, videos, audio, digital humans, motion, environments, shot outputs | S-LIB-01 | TFD-LIB-* | FD-V2 |
| 16 | Organised footage and metadata for external editing | S-PST-01 | TFD-POST-* | FD-V2 (archive export in FD-V1) |

---

## 2. Global interruption and recovery rules

These rules apply to every journey. They extend Gap §8.3 and IA v1.0 §16.

| ID | Interruption | Required behaviour | Requirement |
|---|---|---|---|
| R-01 | One file in a batch fails | Keep its failure record. Every other file continues. The project never shows a misleading "all failed" state | TFD-AST-005 |
| R-02 | AI workflow fails mid-run, or a worker crashes | Prior versions and inputs are preserved. The lease expires and the task is re-claimed. It resumes from the LangGraph checkpoint, not from START. No duplicate candidates are created | TFD-OPS-002/003 |
| R-03 | A canonical version changes while a task runs | The result is marked `stale`. Committing it requires compare and rebase (409 on approve with an old `target_version`) | TFD-APR-003, CTX-003 |
| R-04 | An upstream approved item changes (character, state, location, rule, screenplay, mode) | Downstream packages become `stale`. Approved shots become `review_required` through an impact analysis. Nothing is re-planned automatically | TFD-CON-008, PKG-004 |
| R-05 | A connected submit times out after the provider may have accepted it | The job moves to `unknown_outcome`. It is reconciled by provider request ID or account history before any retry. No automatic duplicate submission | TFD-GEN-003 |
| R-06 | A provider is disconnected, disallowed or down | The same package version stays executable in MANUAL mode. A failed connected submit is never silently duplicated by a manual run | TFD-INT-008 |
| R-07 | Consent is missing, expired or revoked | The gated action is blocked and the block names the missing purpose. Dependent items are flagged. Audit history is kept | TFD-CNS-003/004 |
| R-08 | The session expires mid-edit | Re-authenticate and restore from durable state. Unsaved local edits are offered back. Nothing commits after expiry | STD-RECOVER |
| R-09 | The user lacks a capability | An action-specific block with a request-access path. No data leaks; 404 is returned for objects the user cannot see | TFD-IAM-004 |
| R-10 | A user requests a revision | The old output and package are kept. A new package version and job are created. The disposition and reason are recorded | TFD-OUT-005 |
| R-11 | An AI output fails schema validation | It is rejected and recorded on the run. No candidate is persisted. The user can retry | TFD-AID-003 |
| R-12 | The generator is a mock | The mock label shows on the run, its candidates and the screen. Nothing implies real intelligence | TFD-AID-006 |

---

## 3. Journey (a) — Fully AI feature film

**Persona:** Director (with Story lead, Art lead, Production operator)

**Project:**
- format: Feature film
- mode: `fully_ai`
- delivery profiles: 2.39:1 master, plus a 9:16 trailer cut-down

**Entry:** an existing screenplay draft.

```mermaid
flowchart TD
  A1["S-GLB-02 create project: feature, fully_ai"] --> A2["S-AST-01 upload screenplay PDF"]
  A2 --> A3["S-SCR-01 import as draft v1"]
  A3 --> A4{"Management approves lock?"}
  A4 -- no --> A3b["Director revises in S-SCR-03"] --> A4
  A4 -- yes --> A5["v1 approved_locked and canonical"]
  A5 --> A6["S-SCR-02 run WF-01: scenes and verbatim dialogue"]
  A6 --> A7["S-SCR-04 AI suggestions kept apart"]
  A6 --> A8["S-CHR-01 fictional characters, no performer link"]
  A8 --> A9["S-CST, S-ENV, S-BIB, S-CIN bibles approved"]
  A9 --> A10["S-SEQ, S-SHT shots with virtual camera specs"]
  A10 --> A11["S-MTH-01 methods: fully_ai_generated or digital_human"]
  A11 --> A12["S-PKG-02 compile character reference package"]
  A12 --> A13{"Connected image provider enabled?"}
  A13 -- "FD-V1 or no" --> A14["S-PKG-03 manual export"] --> A15["User runs external tool"] --> A16["S-EXE-02 import and map"]
  A13 -- "FD-V2 yes" --> A17["Cost approval then submit"] --> A18["S-EXE-01 track job"] --> A16
  A16 --> A19["S-OUT-01 inspect vs character spec"]
  A19 -- "request revision" --> A12
  A19 -- approve --> A20["Approved character references become version inputs"]
  A20 --> A21["Keyframes then video packages per shot"]
  A21 --> A22["S-OUT-01 inspect, S-CON-01 continuity across shots"]
  A22 --> A23["S-LIB-01 library"] --> A24["S-PST-01 post handoff JSON, CSV and media"]
```

**Stage walkthrough:**

| Stage | What happens | Persistent result | CURRENT |
|---|---|---|---|
| 1 | Producer picks "Feature film", mode `fully_ai`, quality profile "cinematic", two output profiles | `projects` with template and mode; `output_profiles` | Partial: title/logline/genre only |
| 2 | PDF imported. Management locks v1. Director requests AI pacing suggestions; they stay in the Suggestions Workspace | `screenplay_versions` v1 `approved_locked`; `screenplay_suggestions` | None |
| 3 | WF-01 extracts 118 scenes, dialogue and 14 characters from v1 | `scenes`, `dialogue_segments`, `characters` | WF-01 extracts scenes and uppercase cues from asset bytes; deterministic |
| 4 | Skipped. The film is contemporary fiction. Research screens stay reachable but unused | — | — |
| 5 | Characters are fictional, so no consent applies. Facial identity is defined by text spec until approved references exist | `character_identity_profiles` with provenance | None |
| 6–7 | Locations, environments, Film Bible rules, Cinematography Bible with a virtual camera profile | Bibles approved | Film Bible WF-04 BROKEN |
| 8–9 | Shots get `spec_kind=virtual`, with every camera value `creative_target` or `recommended`. Methods are `fully_ai_generated`; the crowd uses `digital_human` | `shots` | None |
| 11 | Character reference package compiled for a manual image target (or a verified provider in FD-V2) | `production_packages` (hash, references, context hash) | None |
| 12 | FD-V1: manual export and external run. FD-V2: connected submit after cost approval | export record or `generation_jobs` | None |
| 13–14 | Inspector checks identity against the spec. The Director requests one revision, then approves | `output_reviews`, new package v2, approved output | None |
| 15–16 | Approved keyframes and videos organised per shot. Post handoff manifest produced | library; handoff package | None |

**Interruptions specific to (a):**

| Situation | Behaviour |
|---|---|
| A character's costume is changed after 40 video packages were compiled | R-04: the 40 packages go `stale`. S-CON-03 lists them. Each recompiles on demand. Earlier outputs remain in the library with their original lineage |
| The Director wants to adopt an AI-suggested new scene | The suggestion is accepted for revision, then goes through journey (d). The suggestion never alters v1 |
| The video provider changes its schema (FD-V2) | The connection moves to `schema_changed`. Submits are blocked until the snapshot is re-approved. Manual export remains available (R-06) |

---

## 4. Journey (b) — Hybrid chroma historical series

**Persona:** Showrunner/Director, Researcher, Consent manager, On-set/VFX supervisor, DH lead

**Project:**
- format: Episodic historical series (8 episodes)
- mode: `hybrid_live_action`
- real actors are shot on green screen, then transformed into historically accurate characters inside AI-generated Mauryan-era environments

```mermaid
flowchart TD
  B1["S-GLB-02 episodic historical series, hybrid_live_action"] --> B2["Per-episode screenplay lock, S-SCR-01"]
  B2 --> B3["S-RES research brief, claims, timeline"]
  B3 --> B4["S-RES-05 temporal visual profile"]
  B4 --> B5["S-CST-01 costumes and S-ENV-01 environments from evidence"]
  B2 --> B6["S-DH-01 register performers"]
  B6 --> B7{"Consent active for reference_storage and performance_transformation?"}
  B7 -- no --> B7a["Blocked: performer refs and footage refused"]
  B7 -- yes --> B8["S-CHR-01 link performer to character; S-PHY-01 measurements"]
  B8 --> B9["S-SHT-01 shots: live_action_chroma and performance_transformation, physical camera specs"]
  B5 --> B9
  B9 --> B10["S-CAP-01 capture plan per shot, WF-12"]
  B10 --> B11["Shoot day: crew follows plan and manifest"]
  B11 --> B12["S-CAP-02 upload footage, WF-13 analysis"]
  B12 -- "missing clean plate" --> B12a["Recommendation: pickup or AI plate"] --> B11
  B12 --> B13["Footage accepted per shot; actual camera metadata stored"]
  B13 --> B14["S-PKG-02 transformation package: footage plus approved character appearance"]
  B14 --> B15["S-PKG-03 manual or connected execution"]
  B15 --> B16["S-OUT-01 inspect vs source performance and character spec"]
  B16 --> B17["S-LIB-01 then S-PST-01 per episode"]
```

**Sequence: capture to transformation output**

```mermaid
sequenceDiagram
  actor Sup as On-set supervisor
  actor Dir as Director
  participant T as Tattva API
  participant W as Worker WF-12 and WF-13
  participant Ext as External transformation tool
  Dir->>T: approve shot 3.12 method performance_transformation
  Sup->>T: POST workflows/capture-plan for scene 3
  T->>W: enqueue WF-12
  W-->>T: capture plan: chroma distance, markers, clean plate, colour chart, 3/4 refs
  Dir->>T: approve capture manifest
  Sup->>T: upload footage takes for 3.12
  T->>T: consent gate performance_transformation for performer P-07
  T->>W: enqueue WF-13 footage analysis
  W-->>T: issues: spill on left edge, no clean plate, fps 25 consistent
  Sup->>T: link take 4 plus pickup clean plate to manifest items
  Dir->>T: accept take 4 for shot 3.12
  T->>T: compile package with footage, approved costume state, environment refs
  T-->>Sup: export package, manual mode
  Sup->>Ext: run transformation outside Tattva
  Sup->>T: import output and map to shot 3.12
  T->>W: WF-11 inspection vs source: movement, timing, gestures, expressions, intensity, screen direction, position
  W-->>T: findings with method and coverage
  Dir->>T: approve output version 1
```

**Stage notes:**
- **Stage 1:** the episode structure is created. Characters, digital humans and locations are series-scoped; screenplay, shots and capture are episode-scoped (IA §4.2).
- **Stage 4:** claims are typed. Costume details from `historical_interpretation` claims are labelled as such in S-CST-01. Any `creative_dramatization` choice is recorded as a `creative_decision`.
- **Stage 5:** measurements entered by the costume department are `verified` only with a calibrated method. Values estimated from photos stay `estimated`.
- **Stage 7:** physical camera package (manufacturer, sensor, lens series) is defined in S-CIN-01. Shot specs use `metadata_origin=creative_target` until footage arrives, then `actual` from the footage metadata (TFD-HYB-005).
- **Release:** stages 10, 12-connected and 13 (AI-assisted) are FD-V2. In FD-V1 the series is fully planned (stages 1–9, 11), and hybrid shots carry their method ready for capture.

**Interruptions specific to (b):**

| Situation | Behaviour |
|---|---|
| DEC-012/DEC-007 not yet approved | Performer registry and consent screens show "storage disabled pending policy". Planning continues with fictional character specs only. Footage upload of performers is refused with an explanation (R-07) |
| Footage analysis cannot assess tracking adequacy (no model available) | The check is shown as "not assessed (no method)", never "pass" (S-CAP-02) |
| Episode 3 screenplay revised after shooting | Journey (d). The impact analysis lists captured footage and manifests for changed scenes as `review_required`. Footage is never deleted |
| Performer revokes consent mid-season | Journey (f) |

---

## 5. Journey (c) — Mixed mode within one sequence

**Persona:** Director, Cinematographer

**Project:** feature film, mode `mixed`.

**Sequence SQ-07, "The river crossing":**

| Shot | Content | Production method | Notes |
|---|---|---|---|
| 07.01 | Wide establishing shot of the river at dusk | `fully_ai_generated` | Virtual camera |
| 07.02 | Lead actor dialogue | `live_action_chroma` | Physical camera |
| 07.03 | Crowd of soldiers | `digital_human` | Reusable digital humans |
| 07.04 | Lead actor's stunt | `performance_transformation` | Stunt double footage transformed to the lead's approved appearance |
| 07.05 | Close-up | `combined` | Live face plate plus AI armour and environment |

```mermaid
flowchart LR
  P["Project: mixed, no inherited method"] --> SQ["SQ-07 mode null, inherits mixed"]
  SQ --> SC1["Scene 41 mode null"]
  SC1 --> s1["07.01 fully_ai_generated"]
  SC1 --> s2["07.02 live_action_chroma"]
  SC1 --> s3["07.03 digital_human"]
  SC1 --> s4["07.04 performance_transformation"]
  SC1 --> s5["07.05 combined"]
  C1["Character LEAD mode hybrid_live_action"] -. constrains .-> s2
  C1 -. constrains .-> s4
  C1 -. constrains .-> s5
  C1 -. "conflict if LEAD appears in" .-> s1
```

**Steps:**
1. **S-MTH-01:** the Director sees that SQ-07 inherits `mixed`, which means no default method. Each shot must set one, and packaging is blocked until it does (TFD-SHT-002).
2. **S-SHT-01:** the Director sets each method. Shot 07.01 is a wide shot showing the lead's silhouette, but LEAD's character mode is `hybrid_live_action`, so Tattva raises a `mode_conflict` (TFD-PRJ-005). The Director resolves it with a shot-level `creative_decision` ("silhouette only; AI double acceptable at this distance"), and the rationale is recorded.
3. **S-CIN-01 / S-SHT-01:** shots 07.02, 07.04 and 07.05 use the physical camera package. Shots 07.01 and 07.03 use the virtual camera profile, which is **matched to the physical lens look** (focal length equivalence, DoF, colour response) so the cut is seamless. Each value carries `spec_kind` and `metadata_origin`.
4. **S-CON-01:** continuity rules for dimensions `cinematography` (screen direction, lighting direction, colour profile), `environment` (time of day dusk, weather), `costume` and `character_identity` apply **across all five shots regardless of method** (TFD-CON-004).
5. **Execution:**
   - 07.02, 07.04 and 07.05 follow journey (b) capture and transformation.
   - 07.01 and 07.03 follow journey (a) packages.
   - All outputs land on the same sequence.
6. **S-OUT-01 + S-CON-01:** a cross-shot continuity check flags that the light direction in 07.01 (AI) conflicts with the actual lighting in the 07.02 footage. The Director chooses "request correction" on 07.01, which creates a new package version. The real footage is never altered.

```mermaid
stateDiagram-v2
  [*] --> planned
  planned --> method_set: method chosen per shot
  method_set --> mode_conflict: character or effective mode disallows method
  mode_conflict --> method_set: director override with creative decision
  method_set --> capture_pending: hybrid methods
  method_set --> package_ready: AI methods
  capture_pending --> package_ready: footage accepted
  package_ready --> output_review
  output_review --> continuity_conflict: cross-shot check fails
  continuity_conflict --> package_ready: correction requested on chosen shot
  output_review --> approved
  approved --> [*]
```

**Interruptions specific to (c):**

| Situation | Behaviour |
|---|---|
| The project mode is changed from `mixed` to `fully_ai` | S-PRJ-02 shows an impact preview. Shots 07.02/04/05 now fall outside the allowed set for the new effective mode and are flagged `mode_conflict` and `review_required`. They are not changed (TFD-PRJ-006) |
| The live-action shoot for 07.02 is cancelled | The Director switches 07.02 to `digital_human`. The old capture plan is retained as superseded, and a new package is compiled. The continuity rules are unchanged |

---

## 6. Journey (d) — Director-led screenplay revision with management approval and impact analysis

**Persona:** Director (author), Management approver (decision), Producer (impact owner)

```mermaid
sequenceDiagram
  actor Dir as Director
  actor Mgmt as Management approver
  participant T as Tattva API
  participant IA as Impact service
  Dir->>T: POST screenplay-versions/v3/revisions
  T-->>Dir: draft v4 derived_from v3
  Dir->>T: import revised file or edit scenes 12, 18, pull suggestion S-55
  T-->>Dir: change set: scene 12 deleted, scene 18 dialogue changed
  Dir->>T: add justification per change, POST v4/submit
  T->>IA: compute preview impact v3 to v4
  IA-->>T: affected: scene 12 to 9 shots, 3 packages, 2 approved outputs, scene 18 to 14 dialogue segments, 1 localised script
  T->>T: create approval_request level=management target=v4
  T-->>Mgmt: approval in S-APR-01
  Mgmt->>T: GET approval with diff, justification, impact preview
  alt approve
    Mgmt->>T: POST approvals/id/decide approve target_version=v4
    T->>T: lock row, v4 approved_locked, canonical, v3 superseded
    T->>IA: finalise impact_analysis
    IA-->>T: mark affected items review_required, packages stale
    T-->>Dir: notification: v4 locked, 29 items to review
  else reject
    Mgmt->>T: decide reject with notes
    T-->>Dir: v4 rejected, v3 remains canonical
  else request changes
    Mgmt->>T: decide request_changes
    T-->>Dir: v4 back to draft
  end
```

**Rules applied:**
1. The Director can **never** approve their own revision unless they also hold `screenplay.approve_lock`. Even then, a policy flag under DEC-027 can require a second approver.
2. A suggestion pulled from S-SCR-04 is copied into the draft change set. The suggestion record is updated to `accepted_for_revision` and linked to v4.
3. **No automatic propagation:**
   - Shots of the deleted scene 12 are not deleted. They become `review_required`, and the Producer decides to retire or re-anchor each one.
   - Approved outputs stay approved but carry a "source scene superseded" flag.
   - Localised scripts for scene 18 become `review_required` (TFD-VOC-005).
4. Every new shot or sequence created afterwards references v4. Older ones still show v3 until they are reviewed and re-anchored (TFD-SCR-009).

```mermaid
stateDiagram-v2
  [*] --> draft
  draft --> in_review: submit with justification
  in_review --> approved_locked: management approves
  in_review --> rejected: management rejects
  in_review --> draft: request changes
  approved_locked --> superseded: later revision approved
```

**Interruptions specific to (d):**

| Situation | Behaviour |
|---|---|
| v3 is superseded by another approved revision (v5) while v4 is in review | Approving v4 returns 409 (base no longer canonical). Management sees a "rebase required" state. The Director rebases v4 onto v5 and resubmits (R-03) |
| The impact computation fails | The approval stays possible, but the UI shows "impact not computed". Management is warned and can wait or approve. If approved, the impact is computed as a retried task, and items are marked when it completes |
| The management approver's access is revoked while pending | The approval is re-routed to remaining holders (TFD-IAM-008). If none exist, S-TEAM-02 blocks the removal (S-TEAM-02 AC-1) |
| A user tries to edit dialogue on v4 after the lock | 409 `screenplay_locked`, audited (TFD-SCR-003) |

---

## 7. Journey (e) — Manual provider handoff when the API is unavailable

**Persona:** Production operator, Producer

**Context:** FD-V2. A connected video provider is configured, but submissions fail, or a submission's outcome is unknown.

```mermaid
sequenceDiagram
  actor Op as Production operator
  actor Prod as Producer
  participant T as Tattva API
  participant Ad as Provider adapter
  participant P as External provider
  Op->>T: POST packages/PKG-88/submit with Idempotency-Key K1
  T->>T: consent check, cost approval exists by Prod
  T->>Ad: submit attempt A1
  Ad->>P: request
  P--xAd: timeout, no response
  Ad-->>T: outcome unknown
  T->>T: job J1 state unknown_outcome, retry disabled
  T-->>Op: S-EXE-01 shows reconcile required
  Op->>T: POST generation-jobs/J1/reconcile
  T->>Ad: query by provider request id or account history
  alt provider confirms accepted
    Ad-->>T: running
    T->>T: J1 running, continue tracking
  else provider confirms not received
    Ad-->>T: not found
    T->>T: J1 failed_not_submitted
    Op->>T: provider status down: choose manual for same package PKG-88
    T->>T: create manual job J2 linked to PKG-88, J1 closed
    T-->>Op: copy prompt, download JSON and Markdown manifest and ZIP
    Op->>Op: run in external tool UI
    Op->>T: S-EXE-02 import output, map to shot and PKG-88
    T->>T: J2 imported, lineage PKG-88 to J2 to asset
  else cannot determine
    Ad-->>T: indeterminate
    T-->>Op: remain unknown_outcome, manual check in provider account required
    Op->>T: record manual reconciliation result with note
  end
```

```mermaid
stateDiagram-v2
  [*] --> awaiting_approval
  awaiting_approval --> submitted: cost and consent approved
  submitted --> running
  submitted --> unknown_outcome: timeout or lost response
  unknown_outcome --> running: reconciled accepted
  unknown_outcome --> failed_not_submitted: reconciled not received
  running --> succeeded
  running --> failed
  succeeded --> imported
  failed --> [*]
  failed_not_submitted --> [*]
  imported --> [*]
  state manual {
    [*] --> manual_exported
    manual_exported --> awaiting_import
    awaiting_import --> imported_manual
  }
```

**Rules applied:**
1. **No silent fallback.** Tattva never submits the same package manually or connected a second time while the first job is `unknown_outcome` (R-05, R-06).
2. The manual job is a **new job on the same package version**. Lineage is identical in shape to a connected job (TFD-GEN-008).
3. If the provider later delivers J1's output (for example, via a webhook after reconciliation recorded "not received"), it is imported as a separate output linked to J1, and the operator is warned about possible double spend. Neither output overwrites the other.
4. In **FD-V1**, the manual path is the only path. The same screens and package are used, without any connector.
5. Midjourney-type targets (`automation_permitted=false`) only ever show the manual branch (TFD-INT-006).

**Interruptions specific to (e):**

| Situation | Behaviour |
|---|---|
| The package goes `stale` between the failure and the manual export | Export is blocked with "package stale: recompile". The new package version needs a fresh creative approval, and a cost approval if it goes connected again |
| The operator imports an output without knowing which take it is | The import stays `awaiting_mapping`. Metadata is `user_supplied`. No job ID is invented (TFD-OUT-006) |
| The budget cap is reached | Submit is blocked with the cap shown. Manual export is still allowed because Tattva incurs no spend; spend outside Tattva is the user's responsibility, and a notice says so |

---

## 8. Journey (f) — Consent revocation for a performer

**Persona:** Consent manager (Legal), Producer, Director, DH lead

**Context:** performer P-07 had active consents for `reference_storage`, `performance_transformation`, `digital_double` and `voice_clone` on the series in journey (b). P-07 revokes `digital_double` and `voice_clone`.

```mermaid
sequenceDiagram
  actor Legal as Consent manager
  participant T as Tattva API
  participant G as Consent gate
  participant IA as Impact service
  participant Q as Worker
  actor Prod as Producer
  Legal->>T: POST performer-consents/C-31/revoke purposes digital_double, voice_clone, attach revocation letter
  T->>T: C-31 revoked, new consent version C-32 active for remaining purposes, audit
  T->>G: invalidate cached decisions for P-07
  T->>Q: enqueue dependency flagging task
  Q->>IA: find dependents via lineage: digital_humans, avatar_versions, voice_profiles, packages, jobs, outputs
  IA-->>T: DH-3 double, VP-2 voice profile, 6 packages, 2 running jobs, 11 approved outputs
  T->>T: flag all consent_revoked, packages export and submit blocked
  T->>T: running jobs: cancel where provider supports it, else cancellation requested
  T-->>Prod: notification with S-CON-03 consent impact view
  T-->>Legal: agreement obligations panel: retention or deletion of existing outputs per agreement
  Prod->>T: decide per item: retire, replace method, or retain per agreement
  Note over T: Audit events are never deleted. Asset deletion only via the DEC-007 deletion policy path
```

**Rules applied:**
1. **Immediate block.** From the moment of revocation, every gated action for the revoked purposes fails server-side, including requests already in flight that reach the gate later (TFD-CNS-003, TFD-CNS-007).
2. **Remaining purposes stay active.** `reference_storage` and `performance_transformation` remain valid, so the hybrid shots in journey (b) can continue.
3. **Existing outputs:**
   - They are not auto-deleted. Their handling follows the agreement's terms, which are surfaced from the consent record.
   - Deletion, where required, follows the DEC-007 retention and deletion policy and is audited.
   - Library items show `consent_revoked`, and S-PST-01 blocks them from new handoff packages unless the agreement permits use.
4. **Downstream re-planning:** shots that used DH-3 become `review_required`. The Director can switch them to `performance_transformation` (if still consented) or to a fictional `digital_human` not derived from P-07.
5. **Cross-project reuse:** any project reusing DH-3 through S-LIB-02 is flagged as well (TFD-DH-009).

```mermaid
flowchart TD
  R["Revocation recorded"] --> B["Gate blocks revoked purposes immediately"]
  R --> F["Async flagging of dependents"]
  F --> D1["Digital humans and avatar versions: consent_revoked"]
  F --> D2["Voice profiles: disabled"]
  F --> D3["Packages: stale and blocked"]
  F --> D4["Running jobs: cancel or cancellation requested"]
  F --> D5["Approved outputs: flagged; handoff blocked unless agreement permits"]
  D1 --> P["Producer and Director decide per item in S-CON-03"]
  D3 --> P
  D5 --> P
  P --> X1["Retire"]
  P --> X2["Replace method"]
  P --> X3["Retain per agreement, recorded decision"]
```

**Interruptions specific to (f):**

| Situation | Behaviour |
|---|---|
| The flagging task fails partway | The block is already in force, because the gate checks consent live and does not depend on the flags. The flagging task retries (R-02). S-CON-03 shows "dependency scan incomplete" until it finishes |
| A connected job completes after revocation | The output is imported but immediately flagged `consent_revoked`. It cannot be approved for use until Legal records a decision |
| Revocation is entered in error | It cannot be undone by editing. Legal records a new consent version (activated through consent approval), and both events remain in audit |

---

## 9. Mapping of earlier journeys

| Earlier journey | Now covered by |
|---|---|
| PRD v0.9 A (arbitrary input) / IA UJ-01, UJ-02, UJ-03 | Stage 1–3 entry paths; journey (a) |
| PRD v0.9 B (existing bundle) | Stage 1 + R-01 |
| PRD v0.9 C (Kalinga history) / IA UJ-04 | Journey (b), stage 4 |
| PRD v0.9 D (storyboard) / IA UJ-05 | Stage 8 (S-SB-01/02) |
| PRD v0.9 E (character/costume) / IA UJ-06 | Journeys (a) and (b), stage 5 |
| PRD v0.9 F (reference video) | S-AST-03 (P1) |
| PRD v0.9 G (Higgsfield handoff) / IA UJ-08 | Journeys (a) and (e), provider-neutral |
| PRD v0.9 H (import and inspect) / IA UJ-09 | Stages 13–14; journey (e) |
| PRD v0.9 I (change impact) / IA UJ-10 | Journey (d), plus R-04 |
| PRD v0.9 J (interruptions) | §2 R-01…R-12 |
| IA UJ-07 (continuity-aware shots) | Journey (c) |
| IA UJ-11 (alternative direction without changing canon) | Suggestions Workspace + draft revisions. Branches deferred (DEC-029) |
