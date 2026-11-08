"""The capability catalogue and default role-template bundles (ADR-003 §2).

This is the single source of truth: the seed migration, ``AuthzService``, and the
negative authorization test matrix all read from the same two structures here, so a
capability added in one place cannot silently diverge from the others.

A capability is a short, stable string naming one thing a user may be allowed to do,
independent of any specific route or service method. Capabilities are checked against a
*project* (``AuthzService.require``) except where noted as org-level.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    key: str
    description: str


CAPABILITIES: tuple[Capability, ...] = (
    Capability("project.create", "Create a new project (org-level; not scoped to a project)."),
    Capability("project.read", "View a project's details, versions, candidates and canonical state."),
    Capability("project.admin", "Change project-level settings and governance policy."),
    Capability("asset.upload", "Upload a new asset to a project."),
    Capability("workflow.run", "Trigger an intelligence workflow (script, research, storyboard, film bible)."),
    Capability("canon.propose", "Write a canonical record directly (manual research source, film-bible rule)."),
    Capability("approval.creative", "Approve or reject a pending candidate review."),
    Capability("screenplay.approve_lock", "Lock a screenplay version as production-authoritative."),
    Capability("cost.approve", "Approve spend on an external, credit-consuming action."),
    Capability("consent.manage", "Record or revoke a performer's consent/likeness authorization."),
    Capability("likeness.view", "View a performer's sensitive identity references."),
    Capability("voice.view", "View a performer's voice profile or cloned-voice assets."),
    Capability("audit.read", "Read a project's audit trail."),
    Capability("provider.connect", "Connect or configure an external generation provider."),
    Capability("provider.submit", "Submit a job to a connected external provider."),
    Capability("package.export", "Export a production package (manual handoff)."),
    Capability("budget.manage", "Set or change a project's spend budget/cap."),
)

CAPABILITY_KEYS: frozenset[str] = frozenset(c.key for c in CAPABILITIES)

#: ADR-003 §2 "Initial templates". Keys are role_templates.key; order is seed order.
#: `owner` is an org-level membership role (memberships.org_role), not a row here --
#: an org owner holds every capability on every project in their org implicitly
#: (AuthzService.require short-circuits on it) and is never looked up in this table.
DEFAULT_ROLE_TEMPLATES: dict[str, tuple[str, ...]] = {
    #: Auto-granted to whoever creates a project (packages/services/projects.py
    #: ProjectService.create), so a solo creator -- the common case this product is built
    #: for -- can complete every section of the Guided Workspace journey on their own
    #: project without a second role being assigned to them. It is every project-scoped
    #: capability except "project.create" itself, which is org-level and not tied to any
    #: one project. Not meant to be assigned to anyone else by hand; use "management" (for
    #: governance-only access) or a narrower template for that.
    "project_owner": tuple(c.key for c in CAPABILITIES if c.key != "project.create"),
    "management": (
        "project.read",
        "project.admin",
        "approval.creative",
        "screenplay.approve_lock",
        "cost.approve",
        "consent.manage",
        "likeness.view",
        "voice.view",
        "audit.read",
        "budget.manage",
    ),
    "director": (
        "project.read",
        "asset.upload",
        "workflow.run",
        "canon.propose",
        "approval.creative",
        "package.export",
        "provider.submit",
    ),
    "producer": (
        "project.read",
        "asset.upload",
        "workflow.run",
        "cost.approve",
        "provider.connect",
        "provider.submit",
        "budget.manage",
        "package.export",
    ),
    "crew_editor": (
        "project.read",
        "asset.upload",
        "workflow.run",
        "canon.propose",
    ),
    "reviewer": (
        "project.read",
        "approval.creative",
        "audit.read",
    ),
    "viewer": (
        "project.read",
        "audit.read",
    ),
}

for _key, _caps in DEFAULT_ROLE_TEMPLATES.items():
    _unknown = set(_caps) - CAPABILITY_KEYS
    if _unknown:
        raise AssertionError(f"role template {_key!r} references unknown capabilities: {_unknown}")
