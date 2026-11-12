"""Production format template catalogue (D1, TFD-FMT-001). Read-only, authenticated
but not project-scoped -- see packages/domain/format_templates.py."""

from typing import List

from fastapi import APIRouter, Depends

from apps.api.dependencies import get_actor
from apps.api.schemas import FormatTemplateResponse
from packages.domain.format_templates import FORMAT_TEMPLATES
from packages.services.identity import ActorContext

router = APIRouter(prefix="/project-templates", tags=["project-templates"])


@router.get("", response_model=List[FormatTemplateResponse])
def list_project_templates(actor: ActorContext = Depends(get_actor)):
    return [
        FormatTemplateResponse(
            key=t.key,
            name=t.name,
            structure_type=t.structure_type,
            required_workflow_steps=list(t.required_workflow_steps),
            optional_workflow_steps=list(t.optional_workflow_steps),
            default_output_profile=t.default_output_profile,
            note=t.note,
        )
        for t in FORMAT_TEMPLATES
    ]
