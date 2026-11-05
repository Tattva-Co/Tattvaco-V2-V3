# Tattva AI Film Director — UX Strategy & Guided Workspace Specification v1.0

**Status:** UX strategy baseline for design and engineering review  
**Scope:** V1 and V2; V3 editing/finishing remains deferred  
**Primary interaction model:** Online Workspace → Project Workspace → numbered main sections → numbered accordion subsections → completion gate → next main section

## 1. Executive design decision

Tattva should behave as a guided filmmaking workspace, not a dashboard that exposes every capability at once. The first authenticated destination is the **Online Workspace**. From there, users create or resume a project. Within a project, the primary navigation is a 10-stage production journey. Every stage contains numbered accordion groups and smaller actionable subpoints. Required work and approvals determine completion; merely opening a screen never marks work complete.

The interface should be premium and cinematic but operationally restrained: dark workspace chrome and media surfaces, light/neutral reading and form surfaces where useful, strong typography, calm borders, restrained accent colour, and minimal glass effects reserved for transient overlays. The goal is clarity and confidence during long production sessions, not visual novelty.

## 2. Source-based current-state assessment

The supplied Product Evolution & Implementation Gap Report identifies an in-progress Streamlit UI with six navigation destinations, a FastAPI backend, a script-intelligence workflow, PostgreSQL/Alembic persistence, a worker, local immutable storage and tests around script extraction, approval and recovery. The report explicitly does not verify deployed behaviour or test execution. The supplied wireframe specification contains 36 detailed screens. The source material also reports an IA count of 44 and an older PRD inventory of 26 screens; this is a documentation conflict. The recommended action is to establish one canonical screen registry and use the 36-screen wireframe specification as the detailed starting baseline, not to assume the count conflict has been resolved.

### UX implications

- Preserve the existing script-intelligence, candidate review, approval, version and audit concepts.
- Replace the six-destination prototype navigation with a project-centric guided experience only after validating the current frontend architecture and migration plan.
- Keep detailed studio screens available contextually; do not expose them all as equal top-level destinations.
- Keep manual provider handoff a first-class path.
- Do not present mock data as live metrics or successful provider execution.
- Keep all sample values in the prototype labelled illustrative.

## 3. Recommended experience architecture

### Level 0 — Online Workspace

First screen after authentication. It contains Create Project, My Projects, Recent Projects, Continue Working, action queue, approvals, recent activity, notifications and workspace-level team access. It does not expose the full production toolset.

### Level 1 — Project Workspace

Opening a project displays the project header, project selector, current screenplay/version, production mode, project status, next action, overall progress and a compact left-hand journey navigation. The central content area shows only the active main section and its accordion subpoints. An auxiliary Studio Tools index provides direct access to specialist screens for experienced users, subject to permissions and workflow readiness.

### Level 2 — Main sections

Ten numbered main sections form the guided production lifecycle. Sections are ordered by dependencies, but the product is not a rigid wizard: earlier sections remain revisitable; optional and conditional steps can be marked not applicable with a reason; and changes to prior work trigger impact review rather than deleting downstream work.

### Level 3 — Accordion groups and subpoints

Each main section contains numbered accordions (e.g. 04. Character Identity Profile) and numbered actionable subpoints (e.g. 04.2.1 Facial references). For clarity in a compact navigation, the main accordion label may use a parent number such as 04.2, with the nested tasks numbered 04.2.1, 04.2.2. Use stable internal IDs independent of displayed numbering.

## 4. Online Workspace screen

### Primary zones

1. **Global header:** Tattva brand, workspace switcher, search, notifications, help, profile.
2. **Welcome and primary action:** Create New Project and Continue Working.
3. **Project cards:** Thumbnail, title, format, production mode, owner/role, active stage, progress and last updated.
4. **Action queue:** Pending management approvals, assigned reviews, blocked work and due items.
5. **Recent activity:** Meaningful project events with actor, time and target.
6. **Workspace administration:** Team, roles, integrations and workspace settings, shown according to permissions.

### Empty and error states

- No projects: show a concise onboarding prompt and Create Project action.
- No assigned tasks: explain that no action is currently required.
- Partial provider outage: preserve workspace access and show affected integration status; manual workflow remains available.
- API unavailable: show retry/recovery state without implying saved changes.
- No permission: explain the access boundary and provide a request-access route where policy allows.

## 5. Guided project sections and accordion hierarchy

The numbering below is a recommended hierarchy. It is a UX taxonomy and must be reconciled with canonical requirement IDs and the final domain model before engineering hard-codes it.

### 01. Project Workspace & Setup — V1

#### 01.1 Project identity
- **Purpose:** Project title, logline, genre, language, owner and creative brief.
- **Completion rule:** Project details are valid and an owner is assigned.
- **Primary screen(s):** Studio Home / Create Project / Project Overview
#### 01.2 Production format
- **Purpose:** Feature film, OTT series, short, trailer, documentary, vertical film or branded content; configure episode/season structure where applicable.
- **Completion rule:** A production format and required structure are selected.
- **Primary screen(s):** Create Project / Project Settings
#### 01.3 Production mode
- **Purpose:** Three-way choice: Fully AI, Hybrid Live-Action + AI, or Mixed. Allow overrides at sequence, scene and shot level.
- **Completion rule:** A project default is selected; mixed projects can override lower in the hierarchy.
- **Primary screen(s):** Create Project / Production Method Selector
#### 01.4 Creative governance
- **Purpose:** Define management authority, locked screenplay policy, director revision rights and approval rules.
- **Completion rule:** Approval authority and script-governance policy are configured.
- **Primary screen(s):** Team & Permissions / Project Settings
#### 01.5 Delivery profile
- **Purpose:** Aspect ratio, resolution, frame rate, audio, subtitles and delivery targets; allow multiple profiles.
- **Completion rule:** At least one delivery profile exists or is explicitly marked not applicable.
- **Primary screen(s):** Create Project / Project Settings
#### 01.6 Team & permissions
- **Purpose:** Invite members, assign departments, roles, project access and separate approval authority.
- **Completion rule:** Required team roles and approvers are assigned; solo projects may mark team setup not applicable.
- **Primary screen(s):** Team & Permissions
#### 01.7 Project policies
- **Purpose:** Data classification, confidentiality, retention, provider-use rules, performer-consent policy and continuity defaults.
- **Completion rule:** Policy acknowledgement and project defaults are recorded.
- **Primary screen(s):** Project Settings

### 02. Screenplay & Governance — V1

#### 02.1 Import screenplay and source bundle
- **Purpose:** Upload screenplay and supporting documents; preserve original files, checksum, source and version.
- **Completion rule:** An approved script or an explicit development brief is attached; ingestion outcomes are visible.
- **Primary screen(s):** Screenplay Studio / Universal Asset Intake
#### 02.2 Script understanding
- **Purpose:** Parse scenes, sluglines, dialogue, characters, locations, props and source locators; show confidence and parse warnings.
- **Completion rule:** Extraction is completed or reviewed with unresolved parse issues acknowledged.
- **Primary screen(s):** Screenplay Studio / Story Brain
#### 02.3 Scene and dialogue review
- **Purpose:** Inspect scene list, dialogue, characters, scene boundaries and links to source text.
- **Completion rule:** Required scene/dialogue candidates are reviewed or explicitly deferred.
- **Primary screen(s):** Screenplay Studio
#### 02.4 Approved screenplay lock
- **Purpose:** Identify management-approved screenplay version; display lock state and immutable source reference.
- **Completion rule:** A production-authoritative screenplay version is selected and locked by an authorized manager.
- **Primary screen(s):** Screenplay Studio / Approvals & Version History
#### 02.5 AI suggestions workspace
- **Purpose:** Keep alternative dialogue, scene and story suggestions separate from canon; compare against locked source.
- **Completion rule:** Suggestions are either absent, saved as proposals or explicitly marked not required.
- **Primary screen(s):** AI Suggestions Workspace
#### 02.6 Director-led revision
- **Purpose:** Prepare proposed edits, rationale, diff, affected scenes and downstream production impact.
- **Completion rule:** Revision is submitted for approval or explicitly not required.
- **Primary screen(s):** Screenplay Revision & Approval
#### 02.7 Management decision
- **Purpose:** Approve, reject or request changes; approval creates a new locked screenplay version.
- **Completion rule:** All pending screenplay decisions are resolved before production planning relies on the revised script.
- **Primary screen(s):** Screenplay Revision & Approval / Approvals & Version History

### 03. Research & Story Intelligence — V1

#### 03.1 Story Brain
- **Purpose:** Connect script, notes, scenes, characters, relationships, open questions and project context in one intelligence layer.
- **Completion rule:** Core project context has been generated and reviewed for material omissions.
- **Primary screen(s):** Story Brain
#### 03.2 Research brief
- **Purpose:** Define research questions, period, geography, themes, cultural context and required confidence level.
- **Completion rule:** Relevant research scope is captured or marked not applicable.
- **Primary screen(s):** Historical Research Board
#### 03.3 Sources and evidence
- **Purpose:** Capture source metadata, excerpts, locators, dates, reliability, claims and disagreements.
- **Completion rule:** Material claims are linked to evidence or explicitly labelled assumptions/interpretations.
- **Primary screen(s):** Evidence & Source Library
#### 03.4 Historical timeline
- **Purpose:** Map events, character ages, locations, material culture and temporal constraints.
- **Completion rule:** Timeline conflicts are reviewed; unresolved points remain visible.
- **Primary screen(s):** Historical Timeline & Visual Evolution
#### 03.5 Visual and cultural evolution
- **Purpose:** Translate period research into defensible architecture, costume, weapon, material and environment references.
- **Completion rule:** Relevant visual reference requirements are recorded with evidence state.
- **Primary screen(s):** Historical Research Board / Environment Studio
#### 03.6 Research review
- **Purpose:** Separate historical fact, evidence, interpretation, dramatization, assumption and conflict; obtain human approval for canon claims.
- **Completion rule:** Claims that affect production are reviewed or explicitly flagged for later review.
- **Primary screen(s):** Evidence & Source Library / Approvals

### 04. Character & Digital Human Studio — V1 foundation; V2 production integrations

#### 04.1 Character register
- **Purpose:** Create characters from screenplay or manually; link scenes, relationships, role and timeline.
- **Completion rule:** Required characters are identified and source-linked.
- **Primary screen(s):** Character Studio
#### 04.2 Character identity profile
- **Purpose:** Face references, distinguishing features, age appearance, hair, skin, expression and approved identity version.
- **Completion rule:** Required identity attributes and reference images are reviewed.
- **Primary screen(s):** Character Identity Profile
#### 04.3 Physical identity & measurements
- **Purpose:** Manual measurements, AI-assisted estimation, scan imports, units, source, confidence and verification.
- **Completion rule:** Required measurements are entered or imported; estimates remain clearly unverified until human confirmation.
- **Primary screen(s):** Physical Identity & Measurements
#### 04.4 Avatar approach
- **Purpose:** Choose identity-preserving digital double, fictional AI avatar or a combination; define which traits are retained or redesigned.
- **Completion rule:** Avatar approach and preservation rules are approved for applicable characters.
- **Primary screen(s):** Digital Human & Avatar Studio
#### 04.5 Performance references
- **Purpose:** Capture/import facial and body performance, movement references, posture, gestures and source footage.
- **Completion rule:** Required performance references are linked or explicitly not needed.
- **Primary screen(s):** Digital Human & Avatar Studio / On-Set Capture Planner
#### 04.6 Voice profile
- **Purpose:** Original recorded voice or authorized AI voice; language, delivery, accent, approvals and dialogue linkage.
- **Completion rule:** Voice path is selected and rights/consent requirements are satisfied.
- **Primary screen(s):** Voice & Dialogue Studio
#### 04.7 Consent and authorization
- **Purpose:** Purpose-specific likeness, footage, digital-double and voice permissions with scope, evidence and expiry/revocation handling.
- **Completion rule:** Required performer authorization is valid before any derived identity or voice workflow.
- **Primary screen(s):** Character Identity Profile / Team & Permissions
#### 04.8 Character approval & version
- **Purpose:** Review the complete identity, physical, avatar, performance and voice package; version the approved profile.
- **Completion rule:** Director/authorized approver accepts the character profile or records exceptions.
- **Primary screen(s):** Character Studio / Approvals & Version History

### 05. Visual World Development — V1

#### 05.1 Visual direction
- **Purpose:** Define overall art direction, realism/stylization, colour language, materials and references.
- **Completion rule:** A project visual-language profile is approved or intentionally left flexible.
- **Primary screen(s):** Environment & Location Studio
#### 05.2 Location and environment bible
- **Purpose:** Locations, interiors, exteriors, terrain, architecture, atmosphere, geography and environmental states.
- **Completion rule:** Production-relevant locations have approved reference profiles.
- **Primary screen(s):** Environment & Location Studio
#### 05.3 Architecture and materials
- **Purpose:** Period-appropriate construction, material, surface, scale, ageing and evidence references.
- **Completion rule:** Critical visual claims are sourced or labelled as creative interpretation.
- **Primary screen(s):** Environment & Location Studio / Evidence Library
#### 05.4 Costume and appearance
- **Purpose:** Costume sets, armour, footwear, jewellery, hair, makeup, wear/damage and timeline states.
- **Completion rule:** Main character costume states are defined for planned scenes.
- **Primary screen(s):** Costume, Props & Weapons Studio
#### 05.5 Props and weapons
- **Purpose:** Design, scale, materials, ownership, scene state, handling and continuity relationships.
- **Completion rule:** Critical props/weapons are registered and linked to scenes/shots.
- **Primary screen(s):** Costume, Props & Weapons Studio
#### 05.6 Reference asset library
- **Purpose:** Import, tag, compare, version and relate reference images, video, research and generated concepts.
- **Completion rule:** Required reference sets are available or missing references are documented.
- **Primary screen(s):** Production Asset Library
#### 05.7 World continuity approval
- **Purpose:** Approve location, costume, prop and environment states; distinguish intentional variation from inconsistency.
- **Completion rule:** Baseline world references and continuity rules are approved.
- **Primary screen(s):** Continuity & Impact Studio

### 06. Cinematography & Storyboard Studio — V1

#### 06.1 Cinematography bible
- **Purpose:** Visual language, camera grammar, movement principles, framing and lighting approach.
- **Completion rule:** Project cinematography direction is defined or left open with an owner.
- **Primary screen(s):** Cinematography Bible & Camera Library
#### 06.2 Camera package
- **Purpose:** Camera body, sensor, format, codec, frame rate, shutter and exposure metadata; distinguish actual from intended virtual settings.
- **Completion rule:** Physical shoot settings or virtual camera defaults are recorded where relevant.
- **Primary screen(s):** Cinematography Bible & Camera Library
#### 06.3 Lens library
- **Purpose:** Manufacturer, lens series, focal length, aperture, characteristics, focus and desired lens look.
- **Completion rule:** Lens preferences are recorded or AI recommendations are accepted/overridden.
- **Primary screen(s):** Cinematography Bible & Camera Library
#### 06.4 Lighting and exposure
- **Purpose:** Lighting setup, direction, contrast, colour temperature, subject/background separation and continuity.
- **Completion rule:** Lighting intent is defined for production-critical sequences.
- **Primary screen(s):** Cinematography Bible & Camera Library
#### 06.5 Storyboard studio
- **Purpose:** Import or create panels; connect panels to script scenes, sequences, characters and references.
- **Completion rule:** Relevant storyboard panels are mapped or explicitly not required.
- **Primary screen(s):** Storyboard Studio
#### 06.6 Storyboard and script mapping
- **Purpose:** Check coverage, missing panels, scene order and visual continuity.
- **Completion rule:** Coverage gaps are reviewed and accepted or resolved.
- **Primary screen(s):** Storyboard Studio / Sequence Planner
#### 06.7 Shot visual intention
- **Purpose:** Define story purpose, subject, composition, movement, duration, lens intent and reference requirements.
- **Completion rule:** The sequence has enough visual intent to create structured shot specifications.
- **Primary screen(s):** Shot Director

### 07. Production Planning — V1

#### 07.1 Sequence planning
- **Purpose:** Group scenes into sequences; capture narrative purpose, geography, time and dependencies.
- **Completion rule:** Required sequences are structured and linked to approved screenplay version.
- **Primary screen(s):** Sequence Planner
#### 07.2 Shot list
- **Purpose:** Create and order shots with scene, sequence, subject, action, duration, framing and coverage notes.
- **Completion rule:** Required shots are identified and assigned IDs.
- **Primary screen(s):** Shot Director
#### 07.3 Production method per shot
- **Purpose:** Select fully AI, live-action/chroma, performance transformation, digital human or combined method.
- **Completion rule:** Every production-critical shot has a valid method or an approved exception.
- **Primary screen(s):** Production Method Selector
#### 07.4 On-set capture plan
- **Purpose:** For hybrid shots, specify camera/lens, lighting, chroma, tracking, clean plates, performer references and capture manifest.
- **Completion rule:** Capture requirements are prepared or independent footage ingestion is selected.
- **Primary screen(s):** On-Set Capture Planner
#### 07.5 Shot Specification
- **Purpose:** Provider-neutral shot intent, character/environment state, references, constraints and acceptance criteria.
- **Completion rule:** Shot specifications pass schema and completeness validation.
- **Primary screen(s):** Shot Director / Prompt & Production Handoff
#### 07.6 Continuity policy
- **Purpose:** Lock or permit variation at project, character, sequence, scene and shot level.
- **Completion rule:** Continuity rules and exception authority are explicit.
- **Primary screen(s):** Continuity & Impact Studio
#### 07.7 Production readiness
- **Purpose:** Check screenplay version, assets, character/visual bible, shot specs, dependencies, approvals and missing inputs.
- **Completion rule:** Blocking issues are resolved or accepted by authorized roles.
- **Primary screen(s):** Project Overview / Shot Director

### 08. AI Production & Tool Handoff — V1 manual; V2 connected

#### 08.1 Production tool registry
- **Purpose:** List provider, model, verified capability, input/output modes, terms, schema version and last verification.
- **Completion rule:** The intended tool is selectable only in an allowed, verified mode.
- **Primary screen(s):** Production Tool Registry
#### 08.2 AI tool recommendation
- **Purpose:** Compare realism, identity consistency, motion, control, cost, speed, provider policy and shot requirements.
- **Completion rule:** Recommendation reasoning and alternatives are visible; user retains selection.
- **Primary screen(s):** Production Tool Registry
#### 08.3 Prompt and package compiler
- **Purpose:** Compile model-neutral Shot Specification into provider-specific prompt, settings and reference manifest.
- **Completion rule:** Package validates and references the exact source project/shot versions.
- **Primary screen(s):** Prompt & Production Handoff Studio
#### 08.4 Connected execution
- **Purpose:** Use officially supported API/MCP only after schema, permissions, terms, cost, idempotency and output path validation.
- **Completion rule:** Explicit authorized confirmation is captured before external action.
- **Primary screen(s):** External Execution Monitor
#### 08.5 Manual handoff
- **Purpose:** Copy prompts/settings; download JSON/ZIP/reference pack; open external tool; record manual run.
- **Completion rule:** Package can be executed without a connector and retains lineage.
- **Primary screen(s):** Prompt & Production Handoff Studio
#### 08.6 Execution tracking
- **Purpose:** Track queued, submitted, running, completed, failed, unknown outcome, cancelled and reconciled states.
- **Completion rule:** Every run has an honest state and recovery path; unknown outcomes are reconciled before retry.
- **Primary screen(s):** External Execution Monitor
#### 08.7 Cost and usage
- **Purpose:** Estimate/show credits and costs; set caps; record provider charges or user-entered manual spend.
- **Completion rule:** Cost visibility and approval are applied where available; estimates are labelled.
- **Primary screen(s):** Usage & Cost Overview

### 09. Output Inspection & Continuity Approval — V2

#### 09.1 Output import
- **Purpose:** Import generated or transformed media; checksum, validate, preserve original and link to run/package/shot.
- **Completion rule:** Asset is safely stored and has provenance and intended shot mapping.
- **Primary screen(s):** Production Asset Library / External Execution Monitor
#### 09.2 Output inspection
- **Purpose:** Review visual artifacts, framing, exposure, motion, quality, resolution and media integrity.
- **Completion rule:** Required technical checks are passed or findings are recorded.
- **Primary screen(s):** Output Inspector
#### 09.3 Identity and appearance review
- **Purpose:** Compare face, body proportions, costume, props and approved references.
- **Completion rule:** Character and appearance findings have a human disposition.
- **Primary screen(s):** Output Inspector / Continuity Studio
#### 09.4 Performance and motion review
- **Purpose:** Compare timing, gestures, screen direction, expression and motion plausibility against source performance.
- **Completion rule:** Performance deviations are accepted or revision requested.
- **Primary screen(s):** Output Inspector
#### 09.5 World and cinematography review
- **Purpose:** Check environment, lighting, camera intent, lens look, composition and shot continuity.
- **Completion rule:** Director approves or records intentional variation.
- **Primary screen(s):** Continuity & Impact Studio
#### 09.6 Voice and lip-sync review
- **Purpose:** Review audio identity, language, dialogue version, timing, lip-sync and authorization.
- **Completion rule:** Required audio/voice checks are approved or revision requested.
- **Primary screen(s):** Voice & Dialogue Studio / Output Inspector
#### 09.7 Revision request
- **Purpose:** Create versioned revision package with specific findings, reference targets and change scope.
- **Completion rule:** Revision is assigned and does not overwrite prior outputs.
- **Primary screen(s):** Output Inspector / External Execution Monitor
#### 09.8 Shot approval
- **Purpose:** Approve, reject or request changes; preserve reviewer, rationale and output lineage.
- **Completion rule:** Approved output is canonically linked to the shot and project version.
- **Primary screen(s):** Approvals & Version History

### 10. Production Library & Delivery — V1 foundation; V2 expanded

#### 10.1 Approved production library
- **Purpose:** Organize approved images, video, audio, digital humans, motion, references and documents.
- **Completion rule:** Approved assets are discoverable by project, sequence, scene, shot and character.
- **Primary screen(s):** Production Asset Library
#### 10.2 Asset metadata and provenance
- **Purpose:** Track parent asset, derivative, source, provider, model, prompt/package, version, permissions and checksum.
- **Completion rule:** All delivery assets have required lineage and permission metadata.
- **Primary screen(s):** Production Asset Library / Activity & Audit Trail
#### 10.3 Delivery manifest
- **Purpose:** Create shot/scene manifest with media metadata, versions, timecodes where available and notes.
- **Completion rule:** Manifest validation passes for selected delivery profile.
- **Primary screen(s):** Post-Production Handoff
#### 10.4 External editor handoff
- **Purpose:** Prepare Resolve/Premiere handoff profiles and standards-based XML/EDL/AAF/OTIO only when validated.
- **Completion rule:** Handoff package is structurally validated and labelled with supported interchange format.
- **Primary screen(s):** Post-Production Handoff
#### 10.5 Archive and export
- **Purpose:** Export approved artifacts, assets, evidence, prompts, manifests, provider runs and audit/version records.
- **Completion rule:** Export is complete, checksum-verified and access-controlled.
- **Primary screen(s):** Post-Production Handoff / Project Settings
#### 10.6 Project closure and audit
- **Purpose:** Close or archive project; retain required audit and provenance; support restoration/export policy.
- **Completion rule:** Project owner confirms closure conditions and retention policy.
- **Primary screen(s):** Activity & Audit Trail / Project Settings

## 6. Completion and progression rules

### Status model

- **Not Started:** No work saved.
- **In Progress:** Work is saved but required checks remain.
- **Review Required:** Submitted work needs an authorized human decision.
- **Blocked:** A required dependency, permission or approval prevents progress.
- **Ready to Continue:** All required accordion items are complete, approved or validly not applicable.
- **Completed:** The section completion event is persisted.
- **Not Applicable:** The item does not apply to this project; a reason is recorded when required.
- **Changes Required:** A reviewer has returned work for revision.

### Section completion algorithm

1. Resolve applicability for every subpoint from production mode, format, user role and project configuration.
2. Validate required fields, source assets, dependencies and data integrity.
3. Validate approvals required by governance policy.
4. Treat optional items as non-blocking unless a project policy marks them required.
5. Require a reason for marking a normally applicable required item not applicable.
6. If any required item remains incomplete, blocked or review-required, keep the section incomplete and show exact blockers.
7. When all required items pass, set the section to Ready to Continue and show a clear Continue to Next Section action.
8. On user selection, persist the transition and open the next eligible section. Do not unexpectedly redirect while a user is editing.
9. Preserve completed sections as revisitable. Reopening does not erase completion history.
10. If upstream work changes, calculate impacted downstream artifacts and mark them Stale / Review Required. Never silently delete or overwrite downstream work.

### Prototype versus production behaviour

The interactive HTML stores demo progress in browser local storage only. Production progress, completion events, applicability, approvals and downstream invalidation must be authoritative server-side records.

## 7. Conditional production-mode behaviour

Use an explicit three-option segmented selector (not a hidden code-level ternary as a product concept):

- **Fully AI:** AI character, environment, storyboard, keyframe and external video workflows. Chroma capture planning is not applicable unless the project contains a live-action shot.
- **Hybrid Live-Action + AI:** Performer registration, consent, capture plans, chroma checks, footage ingestion, performance transfer/digital-human paths and AI environment integration.
- **Mixed:** Both sets are enabled, with a per-sequence/scene/shot production-method override.

The UI must make clear that project-level mode is a default, not a permanent restriction. Lower-level overrides should show their scope and inherited value.

## 8. Visual design direction

### Recommendation: Cinematic professional workspace

- **Foundation:** Restrained dark application chrome with a calm neutral content canvas; use light surfaces for dense reading, forms and tabular administration when that improves legibility.
- **Typography:** Editorial display typography only for project/film titles; highly readable UI sans-serif for controls, data and instructions. Avoid decorative type for dense workflows.
- **Colour:** Neutral slate/charcoal base; one restrained brand accent; semantic green/amber/red/blue states with sufficient contrast. Avoid encoding meaning by colour alone.
- **Glassmorphism:** Limited to floating command palette, modal or media-overlay surfaces. Do not put primary forms or tables behind blur.
- **Bento layouts:** Use selectively on Online Workspace and Project Overview, not as the default layout for every editing surface.
- **Neumorphism:** Do not use for primary controls because affordance and contrast are less reliable.
- **Motion:** Short, purposeful transitions for accordion, progress and status changes; respect reduced-motion preferences.
- **Density:** Allow compact/comfortable density for professional users; preserve generous spacing around high-risk approvals and consent.

### Style comparison and selection

| Style | Best use in Tattva | Decision |
|---|---|---|
| Minimalist / Swiss | Layout grid, hierarchy, predictable forms and production data | Primary foundation |
| Premium dark workspace | Long-session creative work, project navigation and media review | Primary workspace chrome; pair with neutral content panels |
| Editorial typography | Film/project identity, screenplay context and visual storytelling | Use selectively for titles and narrative surfaces |
| Bento grid | Online Workspace project cards, action queue and project overview | Selective, not universal |
| Glassmorphism | Floating inspector, contextual AI panel, command palette and modal layers | Restrained overlay-only use |
| Neumorphism / soft UI | Raised controls and decorative cards | Avoid for core controls; weak affordance/contrast |
| Gradient-led / maximalist | Hero moments and project thumbnails | Restrict to imagery; not the operating interface |
| Conventional SaaS dashboard | Admin tables, metrics, roles and settings | Use selectively for administrative tasks |

### Design tokens — starting proposal

- **Colour:** app chrome `#0F1721`; primary surface `#F4F5F7`; card `#FFFFFF`; text `#192331`; muted text `#788493`; divider `#DFE4EA`; restrained warm accent `#A98B5B`; semantic success `#2E7052`, warning `#906E2F`, error `#9A4F4F`, info `#506B8B`. Verify contrast before adoption and do not rely on colour alone.
- **Typography:** display 30–36 px for page/project titles; 20–24 px for section titles; 14–16 px body; 11–13 px supporting text; 9–10 px metadata only where readable. Use a highly legible UI sans-serif; editorial type only for selected film identity surfaces.
- **Spacing:** 4 / 8 / 12 / 16 / 24 / 32 / 40 / 48 px scale.
- **Radius:** 6 px compact controls; 8 px buttons/inputs; 12 px cards; 14–16 px overlays.
- **Borders/elevation:** 1 px neutral borders; subtle single-layer shadows; avoid stacking shadows and blur.
- **Grid:** 12-column desktop content grid; max content width about 1440 px; 24–32 px page gutters on desktop; 12–16 px on mobile.
- **Breakpoints:** desktop 1200 px and above; compact laptop/tablet 821–1199 px; tablet 561–820 px; mobile 560 px and below. Validate with real content and touch targets.

## 9. Navigation model

- Workspace-level navigation: Online Workspace, Projects, Action Queue, Team/Administration.
- Project-level guided navigation: 01–10 main sections with progress/status.
- Contextual tools: screens mapped to the active section, opened as panels/subroutes rather than duplicate top-level navigation.
- Global utilities: search, notifications, help, profile, project switcher.
- Breadcrumbs: Online Workspace / Project / Main Section / Accordion / Subpoint.
- Quick access: recent items and pinned tools; access does not bypass permissions or approval requirements.

### Primary user journey patterns

**New project:** Login → Online Workspace → Create Project → Project Workspace → 01 Setup → 02 Screenplay/Governance → 03 Research → 04–07 creative/production design → 08 production package → 09 output review → 10 delivery.

**Existing material:** Online Workspace → Open Project → Universal intake → Asset processing results → source/claim review → resolve only required missing setup → continue at the next eligible section. Do not force users to recreate work already supplied.

**Hybrid scene:** Project mode Hybrid/Mixed → Character/performer registration and purpose-specific consent → per-shot Hybrid method → capture plan or independent footage import → external performance transformation → output inspection → continuity approval.

**Fully AI scene:** Project mode Fully AI/Mixed → character/environment references → provider-neutral Shot Specification → connected provider where verified OR manual package → output import → inspection/approval.

**Management-controlled screenplay change:** Locked script → AI suggestion or director revision proposal → compare diff and impact → management decision → new locked version only on approval → downstream impact review.

**Upstream change:** Edit/replace an approved upstream artifact → compute dependency graph → mark affected downstream artifacts Stale / Review Required → user inspects impact → update/retain with exception/revise. Never silently delete downstream work.

## 10. Existing 36-screen wireframe mapping

The supplied v1.0 screen inventory is retained and reorganized under the 10-stage journey:

| Screen | Existing detailed screen | Guided placement |
|---:|---|---|
| 01 | Studio Home / Online Workspace | Workspace entry |
| 02 | Projects | Workspace entry |
| 03 | Create Project | 01 Project Workspace & Setup |
| 04 | Project Overview | 01 Project Workspace & Setup / cross-stage overview |
| 05 | Team & Permissions | 01 Project Workspace & Setup |
| 06 | Project Settings | 01 Project Workspace & Setup / cross-stage governance |
| 07 | Screenplay Studio | 02 Screenplay & Governance |
| 08 | AI Suggestions Workspace | 02 Screenplay & Governance |
| 09 | Screenplay Revision & Approval | 02 Screenplay & Governance |
| 10 | Story Brain | 03 Research & Story Intelligence |
| 11 | Historical Research Board | 03 Research & Story Intelligence |
| 12 | Historical Timeline & Visual Evolution | 03 Research & Story Intelligence |
| 13 | Evidence & Source Library | 03 Research & Story Intelligence |
| 14 | Character Studio | 04 Character & Digital Human Studio |
| 15 | Character Identity Profile | 04 Character & Digital Human Studio |
| 16 | Digital Human & Avatar Studio | 04 Character & Digital Human Studio |
| 17 | Physical Identity & Measurements | 04 Character & Digital Human Studio |
| 18 | Costume, Props & Weapons Studio | 05 Visual World Development |
| 19 | Environment & Location Studio | 05 Visual World Development |
| 20 | Storyboard Studio | 06 Cinematography & Storyboard Studio |
| 21 | Cinematography Bible & Camera Library | 06 Cinematography & Storyboard Studio |
| 22 | Sequence Planner | 07 Production Planning |
| 23 | Shot Director | 07 Production Planning |
| 24 | Production Method Selector | 07 Production Planning |
| 25 | On-Set Capture Planner | 07 Production Planning |
| 26 | Production Tool Registry | 08 AI Production & Tool Handoff |
| 27 | Prompt & Production Handoff Studio | 08 AI Production & Tool Handoff |
| 28 | External Execution Monitor | 08 AI Production & Tool Handoff |
| 29 | Production Asset Library | 09 Output Inspection / 10 Production Library & Delivery |
| 30 | Output Inspector | 09 Output Inspection & Continuity Approval |
| 31 | Continuity & Impact Studio | 09 Output Inspection & Continuity Approval |
| 32 | Voice & Dialogue Studio | 04 Character / 09 Output Inspection |
| 33 | Approvals & Version History | Cross-stage governance |
| 34 | Post-Production Handoff | 10 Production Library & Delivery |
| 35 | Activity & Audit Trail | Cross-stage governance |
| 36 | Usage & Cost Overview | 08 AI Production & Tool Handoff |

## 11. Core interaction specifications

### Accordion

- Single or multiple accordion expansion should be configurable by section; default to one expanded group in dense sections and allow Expand All / Collapse All.
- Accordion header shows parent number, title, required/optional indicator, status, and completed/total count.
- Keyboard accessible with correct expanded state and focus handling.
- Preserve expanded state when a user navigates to a subpoint and back.
- Search filters accordion groups without changing their canonical numbering.

### Subpoint

- Shows number, title, requirement, inputs, evidence and dependencies.
- Supports Save Draft, Mark Complete, Request Review, Mark Not Applicable (with rationale) and View History, subject to role/policy.
- Never allow a click or view action to mark a subpoint complete automatically.

### Next section

- Show a completion summary: passed items, optional skipped items, unresolved blockers and approvals.
- CTA appears only when the section is Ready to Continue.
- The user chooses Continue to Next Section; previous section remains accessible.

### Change impact

- A change to screenplay, character identity, environment, costume, camera profile or production method triggers impact analysis.
- Affected downstream artifacts are marked Stale / Review Required with an explanation.
- User can inspect affected shots and choose to update, retain with exception, or regenerate/re-export.

## 12. Roles and permissions

Support configurable roles across management, project owner, director, writer, cinematographer, producer, production coordinator, AI artist, research specialist, performer, sound specialist and post-production recipient. Role names are templates, not hard-coded permission bundles. Use project membership and explicit capabilities; approval authority is separately granted. Screenplay locking, performer consent, external spend approval and canonical continuity approval require appropriate server-side permissions.

## 13. Responsive strategy

- **Desktop (primary):** Persistent project journey navigation, main canvas and optional contextual inspector/AI Director side panel.
- **Laptop:** Collapse side panels, preserve journey navigation and provide keyboard shortcuts.
- **Tablet:** Use collapsible journey drawer and stacked content; prioritize reviewing and approval.
- **Mobile:** Prioritize Online Workspace, notifications, approvals, comments, project status and lightweight asset review. Do not squeeze the full storyboard/timeline/shot-planning canvas into mobile.

## 14. Accessibility and usability

Target WCAG 2.2 AA. Provide keyboard navigation, visible focus, semantic labels, screen-reader status updates, sufficient contrast, non-colour status labels, descriptive validation errors, accessible accordion semantics, touch target sizing and reduced-motion support. Explain technical terms progressively; keep advanced camera controls available without requiring new users to understand every parameter.

## 15. Technical and implementation blueprint

- Audit the current Streamlit UI and prototype critical interactions (storyboard, asset inspector, shot planning and media review) before deciding whether to migrate to React/Next.js.
- Keep API/domain contracts independent of UI framework; do not rewrite backend solely to change navigation.
- Persist project stage, accordion/subpoint state, applicability, completion evidence, reviewer decision and invalidation relationships server-side.
- Use stable requirement IDs and internal step IDs; derive visible numbering from the canonical manifest so reordering does not change identity.
- Separate workflow state from canonical product state. A UI completion badge must be derived from server-side rules, not a frontend-only boolean.
- Keep media processing asynchronous; show job state and recovery.
- Keep connected/manual tool execution modes visible and equivalent in lineage.
- Implement feature flags for gradual rollout of the new guided workspace.

## 16. QA and acceptance criteria

1. First authenticated route is Online Workspace.
2. A user can create a project and enter Project Workspace.
3. Project navigation shows the 10 numbered main sections.
4. Every main section displays its numbered accordion hierarchy.
5. Main/accordion numbering is stable and hierarchical.
6. Fully AI, Hybrid and Mixed mode change applicable subpoints correctly.
7. Required task completion is validated; opening a screen does not complete it.
8. Section cannot progress while required approvals or dependencies are unresolved.
9. Ready-to-continue displays a summary and explicit next-section action.
10. Previous sections can be revisited without loss of history.
11. Upstream revisions mark impacted downstream artifacts for review without deleting them.
12. Access and approval controls are permission-aware and server-enforced.
13. Online Workspace, project workspace and accordions have loading, empty, error, offline and permission-denied states.
14. Keyboard and responsive behaviour are verified.
15. No sample metric or provider job is presented as live data.

## 17. Recommended implementation sequence

| Priority | Workstream | Deliverable |
|---|---|---|
| P0 | Source-of-truth reconciliation | Canonical screen registry, requirements map, resolved 26/36/44 screen count discrepancy |
| P0 | Navigation architecture | Online Workspace + Project Workspace shell + 10-stage guided navigation |
| P0 | State model | Persisted statuses, applicability, completion gates, approvals and downstream invalidation |
| P0 | Design system | Tokens, typography, colour, accessibility and reusable accordion/stepper components |
| P1 | Core V1 UX | Screenplay, Story Brain, research, character, world, cinematography and shot-planning screens |
| P1 | Manual tool UX | Production package, copy/export, manual run record, output import and lineage |
| P1 | Governance UX | Roles, screenplay locks, consent, approvals, version and audit |
| P2 | V2 connected execution | Provider registry, verified adapters, job monitor, cost confirmation and inspection |
| P2 | Responsive refinement | Tablet/mobile approval and review flows |

## 18. Design decisions and open risks

- The supplied product sources contain a screen-count conflict (26, 36 and 44). Resolve by publishing one canonical screen manifest; do not delete or duplicate valid capability solely to match a count.
- The current UI baseline is Streamlit according to the architecture decision record. A richer production workspace may justify a new frontend, but require a focused interaction proof and ADR before migration.
- The exact sequence may vary by production type and project readiness; allow conditional paths while preserving a clear default journey.
- Management approval, performer likeness/voice consent and paid provider actions must have explicit, role-controlled gates.
- This UX strategy does not assert that any proposed screen is implemented. It is a design and implementation baseline.
