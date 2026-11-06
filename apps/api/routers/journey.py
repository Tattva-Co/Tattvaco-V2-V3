"""Guided Workspace journey endpoints (GW1; docs/product/JOURNEY_MANIFEST.md)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_actor, get_db
from apps.api.schemas import (
    JourneyGroupResponse,
    JourneyItemActionRequest,
    JourneySectionContinueResponse,
    JourneySectionResponse,
    JourneySubpointResponse,
)
from packages.services.identity import ActorContext
from packages.services.journey import GroupView, JourneyService, SectionView

router = APIRouter(prefix="/projects/{project_id}/journey", tags=["journey"])


def _section_response(view: SectionView) -> JourneySectionResponse:
    return JourneySectionResponse(
        id=view.section.id,
        title=view.section.title,
        release_label=view.section.release_label,
        status=view.status,
        can_continue=view.can_continue,
        groups=[_group_response(g) for g in view.groups],
    )


def _group_response(view: GroupView) -> JourneyGroupResponse:
    g = view.group
    return JourneyGroupResponse(
        id=g.id,
        title=g.title,
        purpose=g.purpose,
        completion_rule=g.completion_rule,
        required=g.required,
        na_policy=g.na_policy,
        release=g.release,
        status=view.status,
        applies=view.applies,
        applicability_reason=view.applicability_reason,
        act_capability=g.act_capability,
        approval_capability=g.approval_capability,
        can_act=view.can_act,
        can_approve=view.can_approve,
        studio_tools=list(g.studio_tools),
        requirements=list(g.requirements),
        subpoints=[
            JourneySubpointResponse(
                id=sp.subpoint.id,
                key=sp.subpoint.key,
                title=sp.subpoint.title,
                kind=sp.subpoint.kind,
                description=sp.subpoint.description,
                status=sp.status,
                not_applicable_reason=sp.not_applicable_reason,
                evidence_refs=sp.evidence_refs,
                notes=sp.notes,
            )
            for sp in view.subpoints
        ],
    )


@router.get("", response_model=List[JourneySectionResponse])
def get_journey(
    project_id: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    views = JourneyService(db).get_journey(actor, project_id)
    return [_section_response(v) for v in views]


@router.post("/items/{jrn_subpoint_id}", response_model=JourneySubpointResponse)
def act_on_journey_item(
    project_id: str,
    jrn_subpoint_id: str,
    req: JourneyItemActionRequest,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    view = JourneyService(db).act_on_item(
        actor,
        project_id,
        jrn_subpoint_id,
        req.action,
        not_applicable_reason=req.not_applicable_reason,
        evidence_refs=req.evidence_refs,
        notes=req.notes,
    )
    return JourneySubpointResponse(
        id=view.subpoint.id,
        key=view.subpoint.key,
        title=view.subpoint.title,
        kind=view.subpoint.kind,
        description=view.subpoint.description,
        status=view.status,
        not_applicable_reason=view.not_applicable_reason,
        evidence_refs=view.evidence_refs,
        notes=view.notes,
    )


@router.post("/sections/{jrn_section_id}/continue", response_model=JourneySectionContinueResponse)
def continue_journey_section(
    project_id: str,
    jrn_section_id: str,
    actor: ActorContext = Depends(get_actor),
    db: Session = Depends(get_db),
):
    result = JourneyService(db).continue_section(actor, project_id, jrn_section_id)
    return JourneySectionContinueResponse(**result)
