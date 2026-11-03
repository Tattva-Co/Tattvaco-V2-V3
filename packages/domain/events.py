"""Domain events emitted during lifecycle mutations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict
import uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_name: str = "domain.event"
    project_id: str = ""
    organization_id: str = ""
    actor_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass
class ProjectCreated(DomainEvent):
    event_name: str = "project.created"


@dataclass
class AssetUploaded(DomainEvent):
    event_name: str = "asset.uploaded"


@dataclass
class WorkflowRunStarted(DomainEvent):
    event_name: str = "workflow.run.started"


@dataclass
class WorkflowRunInterrupted(DomainEvent):
    event_name: str = "workflow.run.interrupted"


@dataclass
class ApprovalDecided(DomainEvent):
    event_name: str = "approval.decided"


@dataclass
class ProjectVersionCommitted(DomainEvent):
    event_name: str = "project.version.committed"
