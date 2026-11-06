# Tattva AI Film Director — Journey Manifest

**Doc ID:** TFD-PRD-JRN-001 · **Version:** 1.0 · **Date:** 2026-11-06 · **Status:** S0.3 deliverable, ready for review

**Machine-readable source:** [`packages/domain/journey_manifest.yaml`](../../packages/domain/journey_manifest.yaml). The YAML is authoritative. The tables in §8 are generated from it, and `tests/unit/test_journey_manifest.py` fails if the two drift apart.

**UX sources (controlling for the Guided Workspace):**
- [UX Strategy & Guided Workspace Specification v1.0](ux/guided-workspace-v1.0/Tattva_AI_Film_Director_UX_Strategy_Guided_Workspace_v1.0.md): §5 hierarchy, §6 completion rules, §7 production modes, §10 screen mapping, §11 interactions, §16 QA.
- [Guided Workspace Wireframe v1.1](ux/guided-workspace-v1.0/Tattva_AI_Film_Director_Guided_Workspace_Wireframe_v1.1.html): the `stages` data (titles, purposes, completion rules, required flags), the subpoint template, section gating and Studio Tools behaviour. Where the wireframe and the UX text differ, the wireframe wins because it is newer. §9 lists every case.

**Consumers:**
- GW1 builds the server-side journey engine from this manifest: the `journey_item_states`, `journey_section_events` and `journey_staleness` tables, the applicability resolver and the section completion algorithm.
- GW2 renders the 10-section journey rail and the accordions from it.
- GW3 hangs the Studio Tools from the catalogue.

---

## 1. Structure

```text
Online Workspace (level 0, not part of the manifest)
└── Project Workspace (level 1)
    └── Section            JRN-04                 "04 Character & Digital Human Studio"   (10)
        └── Group          JRN-04.2               "04.2 Character identity profile"       (70; an accordion)
            └── Subpoint   JRN-04.2.1, JRN-04.2.2 "Review and prepare", "Validate and approve" (140)
```

- **Section:** one of the 10 numbered main sections in the journey rail.
- **Group:** one numbered accordion. It carries the requirement, completion rule, applicability, capabilities and Studio Tools.
- **Subpoint:** an actionable step inside a group. Wireframe v1.1 gives every group the same two subpoints (§4). Status is tracked per subpoint. A group's status is derived from its subpoints, and a section's status from its groups.

## 2. Identity and numbering (DEC-011)

- IDs are `JRN-<section>.<group>` for groups and `JRN-<section>.<group>.<item>` for subpoints. They are assigned once and **never change**. Reordering, renaming or moving an item keeps its ID.
- Visible numbers (`04`, `04.2`, `04.2.1`) are **derived from list order** at render time. Today the visible number and the ID coincide. If they diverge after a reorder, the UI shows the derived number and the server stores the ID.
- Retire an item with `retired: true`. Never delete an ID and never reuse one, because `journey_item_states` rows and audit events reference it.
- UX §11: search filters accordions but never changes their numbering.

## 3. Group fields

| Field | Meaning |
|---|---|
| `id`, `title` | Stable ID and display title (wireframe v1.1) |
| `purpose` | What the step is for (wireframe `description`) |
| `completion_rule` | Human-readable rule (wireframe `completion`) |
| `required` | Blocks section completion when true (UX §6, step 4). All 70 are required in wireframe v1.1, and a project policy can't make them optional in v1 |
| `na` | `never`: the group can't be marked not applicable. `reason_required`: marking it not applicable needs a recorded reason (UX §6, step 5) |
| `release` | `v1`, `v1_v2` (introduced in FD-V1, expanded in FD-V2) or `v2`. A group whose release isn't shipped is **absent**, not shown as a teaser (IA §4.2, rule 4) |
| `applicability` | When the group applies (§5) |
| `act_capability` | Capability needed to work on the group: Save Draft, Mark Complete, Request Review, Mark Not Applicable. Keys come from `packages/domain/capabilities.py` |
| `approval_capability` | Capability needed to pass the `validate` subpoint when it is a real approval. `null` means the actor with `act_capability` self-validates |
| `completion_check` | `manual_with_evidence`: a user with the capability marks it complete and attaches evidence refs. `system`: the server derives completion from domain state (§6) |
| `studio_tools` | Canonical `S-` screens that do the work (§7) |
| `requirements` | Linked `TFD-` requirements in `PRD_v1.0.md` |

## 4. Subpoint template (wireframe v1.1)

| Suffix | Key | Title | Kind | Completes when |
|---|---|---|---|---|
| `.1` | `prepare` | Review and prepare | `work` | The source material, responsible owner and required decisions are confirmed, and the evidence refs are recorded |
| `.2` | `validate` | Validate and approve | `review_gate` | Completeness, links, permissions and any approval have **actually passed** in the backing workflow. Prior versions are preserved and exceptions recorded |

A group that later needs specific subpoints lists them explicitly with new, permanent IDs. The template IDs `.1` and `.2` stay reserved for that group.

## 5. Applicability (UX §6 step 1; UX §7)

The resolver evaluates every group for the project and stores the result with a reason in `journey_item_states.applicability`:

1. **Release.** If the group's `release` isn't enabled in this deployment, the group is absent.
2. **Mode.** `modes: all`, or a list of `fully_ai`, `hybrid_live_action` and `mixed`. The effective project mode (TFD-PRJ-003) is used.
3. **Exceptions.** If `unless_any` holds any true condition, the group applies even when its mode doesn't match. The only supported condition today is:
   - `shot_method_in: [methods]`, which is true when any non-retired shot has one of those `production_method` values (TFD-SHT-002).
4. A group that doesn't apply because of its mode is **shown** with status `not_applicable` and the text "Not applicable for the selected production mode" (wireframe v1.1). It isn't hidden, so a mixed project can see what would switch on.

Mode rules in v1 of the manifest:

| Group | Fully AI | Hybrid | Mixed | Source |
|---|---|---|---|---|
| `JRN-07.4` On-set capture plan | Not applicable, **unless** a shot uses `live_action_chroma` or `performance_transformation` | Applies | Applies | Wireframe v1.1 `applicable()`; UX §7 |
| `JRN-04.7` Consent and authorization | **Applies** (a real likeness or voice can still be used) | Applies | Applies | Wireframe v1.1 keeps it applicable explicitly. "No real performers" is a valid N/A reason |
| All other groups | Applies | Applies | Applies | — |

Format and role:
- **Format** changes the *fields* inside a group (for example, episode structure in `JRN-01.2`), not whether the group applies.
- **Role** changes what a user *can do* (`act_capability`, `approval_capability`), not whether the group applies to the project.
- Users without the capability see the group read-only, with the reason (UX §16, item 12).

## 6. Status and completion (UX §6)

**Subpoint and group statuses:** `not_started`, `in_progress`, `review_required`, `changes_required`, `blocked`, `completed`, `not_applicable` and `stale`.
A group is `completed` when both subpoints are completed, or when the group is `not_applicable` with its reason recorded.

**Section statuses:** `not_started`, `in_progress`, `blocked`, `ready_to_continue` and `completed`.

**Section completion algorithm** (implemented server-side in GW1; the UI never computes it):
1. Resolve applicability for every group (§5).
2. Validate the required fields, source assets, dependencies and data integrity behind each `completed` claim. For `system` checks, the server derives the result.
3. Validate the approvals that governance requires (`approval_capability`).
4. Optional groups don't block. There are none in v1.
5. Not-applicable requires a reason unless the group was made not applicable automatically by mode. Groups with `na: never` reject it.
6. If any applicable required group is incomplete, `blocked` or `review_required`, the section stays incomplete and the exact blockers are listed.
7. When every group passes, the section becomes `ready_to_continue` and shows the completion summary and the **Continue to Next Section** action.
8. Only the user's explicit Continue persists the transition (a `journey_section_events` row) and opens the next section. The server never moves the user on (`gating.auto_advance: false`).
9. Completed sections stay revisitable. Reopening never erases completion history.
10. When upstream work changes, affected downstream groups are marked `stale` with an explanation (`journey_staleness`). Nothing is silently deleted or overwritten.

**Opening a screen never completes anything** (UX §11, wireframe v1.1). Completion comes only from an explicit action backed by persisted evidence or a `system` check.

**System checks** derive completion from data that already exists in the G-01 to G-04 slices:

| Key | Group | True when |
|---|---|---|
| `screenplay_asset_present` | `JRN-02.1` | The project has a script asset that ingested successfully |
| `workflow_completed:script_intelligence` | `JRN-02.2` | At least one WF-01 run completed for the project |
| `no_pending_candidates:script_intelligence` | `JRN-02.3` | No WF-01 candidates are still `proposed` |
| `research_questions_present` | `JRN-03.2` | The project has at least one research question |
| `no_pending_candidates:historical_research` | `JRN-03.6` | No WF-02 candidates are still `proposed` |
| `approved_rules_present:film_bible` | `JRN-05.1` | At least one approved Film Bible rule exists |
| `no_pending_candidates:storyboard_intelligence` | `JRN-06.5` | No WF-03 candidates are still `proposed` |

All other groups use `manual_with_evidence` until their D-stage slice adds domain state worth deriving from. Switching a group to `system` is a manifest change plus a GW1 check.

## 7. Gating and Studio Tools

- **Section unlock (wireframe v1.1):** a section is selectable in the journey rail once the previous section is `ready_to_continue` or `completed`. Section 01 is always open. Selecting a locked section shows "Complete the required work in the previous section first."
- **Not a rigid wizard (UX §3):** completed sections are always revisitable, and the **Studio Tools Index** opens any specialist screen directly, subject to permissions.
- **Studio Tools never bypass gates:** opening a tool doesn't complete a step, and a tool's own approvals remain the only way to approve. This is the wireframe v1.1 Studio Tools Index text, and it reconciles the gated rail with IA §4.1 "every stage is reachable directly".
- The **catalogue** (`studio_tools` in the YAML) lists all 61 canonical screens, each with a `home` (`workspace`, `cross_stage` or a section) and its wireframe v1.1 screen numbers. The full mapping is in `INFORMATION_ARCHITECTURE.md` §3A.

## 8. Journey content (generated from the YAML)

Don't edit these tables by hand. Change the YAML, then run `python scripts/generate_journey_tables.py`.

Legend:
- **Rel.** = release
- **N/A** = not-applicable policy
- **Act / Approve** = capabilities
- **Check:** `M` = manual with evidence, `S` = system

<!-- BEGIN GENERATED: journey tables -->

### 01 Project Workspace & Setup — V1

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-01.1` | Project identity | V1 | never | all | project.admin | M | S-GLB-02, S-PRJ-01, S-PRJ-02 | TFD-PRJ-001, TFD-PRJ-002 |
| `JRN-01.2` | Production format | V1 | never | all | project.admin | M | S-GLB-02, S-PRJ-02 | TFD-FMT-001, TFD-FMT-003, TFD-FMT-004, TFD-FMT-005 |
| `JRN-01.3` | Production mode | V1 | never | all | project.admin | M | S-GLB-02, S-MTH-01 | TFD-PRJ-003, TFD-PRJ-004, TFD-PRJ-005, TFD-PRJ-006 |
| `JRN-01.4` | Creative governance | V1 | never | all | project.admin | M | S-TEAM-02, S-PRJ-02 | TFD-IAM-005, TFD-SCR-002, TFD-APR-007 |
| `JRN-01.5` | Delivery profile | V1 | reason required | all | project.admin | M | S-GLB-02, S-PRJ-02 | TFD-FMT-002 |
| `JRN-01.6` | Team & permissions | V1 | reason required | all | project.admin | M | S-TEAM-02, S-TEAM-01 | TFD-IAM-002, TFD-IAM-003, TFD-IAM-004, TFD-IAM-008 |
| `JRN-01.7` | Project policies | V1 | reason required | all | project.admin | M | S-PRJ-02 | TFD-INT-006, TFD-CNS-002, TFD-IAM-007 |

### 02 Screenplay & Governance — V1

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-02.1` | Import screenplay and source bundle | V1 | reason required | all | asset.upload | S `screenplay_asset_present` | S-AST-01, S-SCR-01 | TFD-SCR-001, TFD-AST-001, TFD-AST-002, TFD-AST-004, TFD-AST-005, TFD-AST-006 |
| `JRN-02.2` | Script understanding | V1 | reason required | all | workflow.run | S `workflow_completed:script_intelligence` | S-SCR-02, S-BRN-01 | TFD-STY-001, TFD-STY-002, TFD-STY-003, TFD-SCR-004 |
| `JRN-02.3` | Scene and dialogue review | V1 | reason required | all | workflow.run / approval.creative | S `no_pending_candidates:script_intelligence` | S-SCR-02, S-APR-02 | TFD-STY-001, TFD-STY-002, TFD-APR-004 |
| `JRN-02.4` | Approved screenplay lock | V1 | reason required | all | canon.propose / screenplay.approve_lock | M | S-SCR-01, S-APR-02 | TFD-SCR-002, TFD-SCR-003, TFD-IAM-005 |
| `JRN-02.5` | AI suggestions workspace | V1 | reason required | all | workflow.run | M | S-SCR-04 | TFD-SCR-005 |
| `JRN-02.6` | Director-led revision | V1 | reason required | all | canon.propose | M | S-SCR-03 | TFD-SCR-006, TFD-SCR-010 |
| `JRN-02.7` | Management decision | V1 | reason required | all | screenplay.approve_lock / screenplay.approve_lock | M | S-SCR-03, S-APR-02 | TFD-SCR-007, TFD-SCR-008, TFD-SCR-010 |

### 03 Research & Story Intelligence — V1

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-03.1` | Story Brain | V1 | reason required | all | workflow.run | M | S-BRN-01, S-BRN-02 | TFD-STY-004, TFD-STY-005, TFD-STY-006, TFD-CTX-001 |
| `JRN-03.2` | Research brief | V1 | reason required | all | canon.propose | S `research_questions_present` | S-RES-01, S-RES-02 | TFD-RES-001, TFD-RES-007 |
| `JRN-03.3` | Sources and evidence | V1 | reason required | all | canon.propose | M | S-RES-03 | TFD-RES-002, TFD-RES-003 |
| `JRN-03.4` | Historical timeline | V1 | reason required | all | canon.propose | M | S-RES-04 | TFD-RES-006 |
| `JRN-03.5` | Visual and cultural evolution | V1 | reason required | all | canon.propose | M | S-RES-05, S-ENV-01 | TFD-RES-008, TFD-RES-009 |
| `JRN-03.6` | Research review | V1 | reason required | all | canon.propose / approval.creative | S `no_pending_candidates:historical_research` | S-RES-02, S-RES-03, S-APR-02 | TFD-RES-004, TFD-RES-005, TFD-APR-004 |

### 04 Character & Digital Human Studio — V1 foundation; V2 production integrations

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-04.1` | Character register | V1 | reason required | all | canon.propose | M | S-CHR-01, S-CHR-02 | TFD-CHR-009, TFD-STY-003, TFD-CHR-008 |
| `JRN-04.2` | Character identity profile | V1 | reason required | all | canon.propose | M | S-CHR-01 | TFD-CHR-001, TFD-CHR-002, TFD-CHR-005 |
| `JRN-04.3` | Physical identity & measurements | V1→V2 | reason required | all | canon.propose | M | S-PHY-01 | TFD-PHY-001, TFD-PHY-002, TFD-PHY-003, TFD-PHY-004, TFD-PHY-006, TFD-PHY-005, TFD-PHY-007 |
| `JRN-04.4` | Avatar approach | V1→V2 | reason required | all | canon.propose / approval.creative | M | S-CHR-01, S-DH-02 | TFD-DH-010, TFD-DH-001, TFD-DH-002, TFD-DH-003 |
| `JRN-04.5` | Performance references | V1→V2 | reason required | all | canon.propose | M | S-CHR-01, S-DH-02, S-CAP-01 | TFD-CHR-003, TFD-DH-004, TFD-DH-008 |
| `JRN-04.6` | Voice profile | V1→V2 | reason required | all | canon.propose | M | S-CHR-01, S-VOC-01 | TFD-VOC-001, TFD-CNS-005, TFD-VOC-003, TFD-VOC-004 |
| `JRN-04.7` | Consent and authorization | V1 | reason required | all | consent.manage / consent.manage | M | S-DH-01 | TFD-CNS-001, TFD-CNS-002, TFD-CNS-003, TFD-CNS-004, TFD-CNS-005, TFD-IAM-007 |
| `JRN-04.8` | Character approval & version | V1 | reason required | all | canon.propose / approval.creative | M | S-CHR-01, S-APR-02 | TFD-CHR-006, TFD-VER-002 |

### 05 Visual World Development — V1

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-05.1` | Visual direction | V1 | reason required | all | workflow.run / approval.creative | S `approved_rules_present:film_bible` | S-BIB-01, S-BIB-02, S-ENV-01 | TFD-CIN-010, TFD-CIN-011, TFD-CIN-012, TFD-CIN-013 |
| `JRN-05.2` | Location and environment bible | V1 | reason required | all | canon.propose / approval.creative | M | S-ENV-01 | TFD-ENV-001, TFD-ENV-002, TFD-ENV-004 |
| `JRN-05.3` | Architecture and materials | V1 | reason required | all | canon.propose | M | S-ENV-01, S-RES-03 | TFD-ENV-001, TFD-PRP-003, TFD-RES-008 |
| `JRN-05.4` | Costume and appearance | V1 | reason required | all | canon.propose | M | S-CST-01 | TFD-CST-001, TFD-CST-002, TFD-CST-003, TFD-CHR-004, TFD-CHR-007 |
| `JRN-05.5` | Props and weapons | V1 | reason required | all | canon.propose | M | S-CST-02 | TFD-PRP-001, TFD-PRP-002, TFD-PRP-003 |
| `JRN-05.6` | Reference asset library | V1 | reason required | all | asset.upload | M | S-AST-02, S-AST-03 | TFD-AST-003, TFD-AST-007, TFD-ENV-003 |
| `JRN-05.7` | World continuity approval | V1 | reason required | all | canon.propose / approval.creative | M | S-CON-01 | TFD-CON-002, TFD-CON-003, TFD-CON-006 |

### 06 Cinematography & Storyboard Studio — V1

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-06.1` | Cinematography bible | V1 | reason required | all | canon.propose | M | S-CIN-01 | TFD-CIN-005 |
| `JRN-06.2` | Camera package | V1 | reason required | all | canon.propose | M | S-CIN-01 | TFD-CIN-001, TFD-CIN-002, TFD-CIN-003 |
| `JRN-06.3` | Lens library | V1 | reason required | all | canon.propose | M | S-CIN-01 | TFD-CIN-001, TFD-CIN-004 |
| `JRN-06.4` | Lighting and exposure | V1 | reason required | all | canon.propose | M | S-CIN-01 | TFD-CIN-005, TFD-CIN-006 |
| `JRN-06.5` | Storyboard studio | V1 | reason required | all | workflow.run / approval.creative | S `no_pending_candidates:storyboard_intelligence` | S-SB-01 | TFD-SB-001, TFD-SB-002, TFD-SB-004 |
| `JRN-06.6` | Storyboard and script mapping | V1 | reason required | all | canon.propose | M | S-SB-02, S-SEQ-01 | TFD-SB-003 |
| `JRN-06.7` | Shot visual intention | V1 | reason required | all | canon.propose | M | S-SHT-01 | TFD-SHT-006, TFD-CIN-004 |

### 07 Production Planning — V1

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-07.1` | Sequence planning | V1 | reason required | all | canon.propose | M | S-SEQ-01, S-SEQ-02 | TFD-SEQ-001, TFD-SEQ-002 |
| `JRN-07.2` | Shot list | V1 | reason required | all | canon.propose | M | S-SHT-01 | TFD-SHT-001 |
| `JRN-07.3` | Production method per shot | V1 | reason required | all | canon.propose | M | S-MTH-01 | TFD-SHT-002, TFD-PRJ-004, TFD-PRJ-005 |
| `JRN-07.4` | On-set capture plan | V1→V2 | reason required | hybrid_live_action, mixed; unless shot_method_in: live_action_chroma, performance_transformation | canon.propose / approval.creative | M | S-CAP-01, S-CAP-02 | TFD-HYB-001, TFD-HYB-002, TFD-HYB-003, TFD-HYB-004 |
| `JRN-07.5` | Shot Specification | V1 | reason required | all | canon.propose / approval.creative | M | S-SHT-01, S-PKG-02 | TFD-SHT-003, TFD-SHT-004, TFD-SHT-005 |
| `JRN-07.6` | Continuity policy | V1 | reason required | all | canon.propose | M | S-CON-01 | TFD-CON-002, TFD-CON-003, TFD-CON-004 |
| `JRN-07.7` | Production readiness | V1 | never | all | canon.propose / approval.creative | M | S-PRJ-01, S-AID-01, S-SHT-01 | TFD-AID-001, TFD-CON-001, TFD-CON-005, TFD-PRJ-007 |

### 08 AI Production & Tool Handoff — V1 manual; V2 connected

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-08.1` | Production tool registry | V1→V2 | reason required | all | project.admin | M | S-REG-01, S-REG-02 | TFD-INT-003, TFD-INT-004, TFD-INT-006 |
| `JRN-08.2` | AI tool recommendation | V1→V2 | reason required | all | package.export | M | S-REG-01, S-PKG-02 | TFD-PKG-006 |
| `JRN-08.3` | Prompt and package compiler | V1 | reason required | all | package.export | M | S-PKG-01, S-PKG-02 | TFD-PKG-001, TFD-PKG-002, TFD-PKG-003, TFD-PKG-004, TFD-PKG-005, TFD-PKG-007 |
| `JRN-08.4` | Connected execution | V2 | reason required | all | provider.submit / cost.approve | M | S-PKG-03, S-EXE-01, S-REG-02 | TFD-INT-002, TFD-INT-005, TFD-GEN-001, TFD-GEN-002, TFD-GEN-004, TFD-CNS-007, TFD-CNS-008 |
| `JRN-08.5` | Manual handoff | V1 | reason required | all | package.export | M | S-PKG-03 | TFD-INT-001, TFD-INT-004 |
| `JRN-08.6` | Execution tracking | V1→V2 | reason required | all | package.export | M | S-EXE-01 | TFD-INT-004, TFD-GEN-001, TFD-GEN-003, TFD-GEN-008, TFD-OPS-005 |
| `JRN-08.7` | Cost and usage | V2 | reason required | all | budget.manage / cost.approve | M | S-USE-01 | TFD-GEN-004, TFD-IAM-006, TFD-AID-007 |

### 09 Output Inspection & Continuity Approval — V1 manual review; V2 assisted inspection

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-09.1` | Output import | V1 | reason required | all | asset.upload | M | S-EXE-02, S-EXE-01 | TFD-OUT-001, TFD-OUT-006 |
| `JRN-09.2` | Output inspection | V1→V2 | reason required | all | approval.creative | M | S-OUT-01 | TFD-OUT-002 |
| `JRN-09.3` | Identity and appearance review | V1→V2 | reason required | all | approval.creative | M | S-OUT-01, S-CON-01 | TFD-OUT-002, TFD-CON-007 |
| `JRN-09.4` | Performance and motion review | V1→V2 | reason required | all | approval.creative | M | S-OUT-01 | TFD-OUT-002, TFD-OUT-003 |
| `JRN-09.5` | World and cinematography review | V1→V2 | reason required | all | approval.creative / approval.creative | M | S-CON-01, S-OUT-01 | TFD-OUT-002, TFD-CON-004, TFD-CIN-006 |
| `JRN-09.6` | Voice and lip-sync review | V2 | reason required | all | approval.creative / approval.creative | M | S-VOC-01, S-VOC-02, S-OUT-01 | TFD-VOC-004, TFD-VOC-006, TFD-VOC-007 |
| `JRN-09.7` | Revision request | V1→V2 | reason required | all | canon.propose | M | S-OUT-01, S-EXE-01 | TFD-OUT-005 |
| `JRN-09.8` | Shot approval | V1 | never | all | approval.creative / approval.creative | M | S-APR-02 | TFD-OUT-004, TFD-APR-001, TFD-APR-003 |

### 10 Production Library & Delivery — V1 foundation; V2 expanded

| ID | Group | Rel. | N/A | Applies | Act / Approve | Check | Studio Tools | Requirements |
|---|---|---|---|---|---|---|---|---|
| `JRN-10.1` | Approved production library | V1→V2 | reason required | all | package.export | M | S-LIB-01, S-AST-02 | TFD-LIB-001 |
| `JRN-10.2` | Asset metadata and provenance | V1→V2 | reason required | all | canon.propose | M | S-LIB-01, S-APR-03 | TFD-LIB-002, TFD-VER-004, TFD-AST-004 |
| `JRN-10.3` | Delivery manifest | V1→V2 | reason required | all | package.export | M | S-PST-01 | TFD-POST-001, TFD-POST-002, TFD-POST-003 |
| `JRN-10.4` | External editor handoff | V2 | reason required | all | package.export | M | S-PST-01 | TFD-POST-001, TFD-POST-002 |
| `JRN-10.5` | Archive and export | V1 | reason required | all | package.export | M | S-PST-01, S-PRJ-02 | TFD-POST-004, TFD-AUD-003 |
| `JRN-10.6` | Project closure and audit | V1 | reason required | all | project.admin / project.admin | M | S-APR-03, S-PRJ-02 | TFD-PRJ-002, TFD-AUD-001, TFD-AUD-002 |

<!-- END GENERATED: journey tables -->

## 9. Decisions taken while building the manifest

| # | Topic | Sources in tension | Decision |
|---|---|---|---|
| JM-1 | Section 09 release | UX §5 labels all of 09 V2. Plan D9 and IA §6 put manual import, inspection and shot approval in FD-V1 | Each group carries its own release. 09.1 and 09.8 are `v1`; 09.2–09.5 and 09.7 are `v1_v2` (manual in V1, assisted in V2); 09.6 is `v2` |
| JM-2 | Capture plan release (`JRN-07.4`, S-CAP-01) | IA §6 says V2 only. Plan D7 (approved later) says "capture plan record (V1 manual form; WF-12 automation in V2)" | `v1_v2`. IA v1.1 moves S-CAP-01 to `[V1→V2]` |
| JM-3 | Production library (`JRN-10.1`, S-LIB-01) | IA §6 and TFD-LIB-001 say V2. Plan D9 and UX §5 say "V1 foundation" | `v1_v2`. IA v1.1 moves S-LIB-01 to `[V1→V2]` |
| JM-4 | Usage & Cost Overview (wireframe screen 36) | No IA screen existed | New screen **S-USE-01** `[V2]` (TFD-GEN-004, TFD-IAM-006), homed in section 08 |
| JM-5 | Reference asset library (`JRN-05.6`) | The wireframe names "Production Asset Library" | Reference *inputs* use S-AST-02/03. S-LIB-01 is approved *outputs* (IA §3), used in section 10 |
| JM-6 | Gated rail vs "not a wizard" | Wireframe v1.1 locks forward sections. IA §4.1 says every stage is reachable | The rail is gated and the Studio Tools Index is open (§7). Both rules hold |
| JM-7 | "Hide by mode" | IA §4.2 rule 2 says never hide by mode. The wireframe shows mode-N/A groups greyed out | Groups are shown with status `not_applicable` and never hidden. Studio Tools stay visible in every mode |
| JM-8 | Required flags | Wireframe v1.1 marks all 70 required. Several UX completion rules allow "not required" | All are required. Escape hatch: `na: reason_required`. `na: never` applies to 01.1–01.4, 07.7 and 09.8 |
| JM-9 | Subpoints | UX §3 describes item-specific subpoints (e.g. 04.2.1 Facial references) but doesn't enumerate them. Wireframe v1.1 uses a uniform two-step template | Use the wireframe template now. Domain-specific subpoints get added in the D-stages with new IDs (§4) |
| JM-10 | `combined` and `digital_human` methods in the 07.4 exception | UX §7 says "unless the project contains a live-action shot" | Only `live_action_chroma` and `performance_transformation` trigger the exception for now. Revisit in D7 when the methods are modelled |
