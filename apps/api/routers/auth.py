"""Local-development authentication (ADR-003, approval gate 1).

This router is mounted ONLY when ``environment == "development"`` (see
``apps/api/main.py::create_app``). It does not exist in ``test`` (which uses the
``X-Actor-ID`` header) or in ``staging``/``production`` (which require a real OIDC
provider). There is no backdoor here for those environments: the route is never
registered, so it 404s, and ``get_actor`` never accepts its tokens outside
``development``/``test`` (a dev token's issuer is checked against ``tattva-dev``).

This stands in for "log in" while no external identity provider is configured. A human
(or the future web app) posts an email; a user row is created if one doesn't already
exist under the fixed ``default-studio`` organization; a short-lived signed token comes
back. It is explicit and auditable, unlike the previous "missing header silently becomes
some user in some organization" behaviour it replaces.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db, get_settings
from apps.api.schemas import DevLoginRequest, DevLoginResponse
from packages.core.config import Settings
from packages.persistence.repositories import UserRepository
from packages.services.auth import DevTokenAuthProvider

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-login", response_model=DevLoginResponse)
def dev_login(
    req: DevLoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = UserRepository(db).get_or_create_dev_user(req.email, req.full_name)
    db.commit()

    issuer = DevTokenAuthProvider(settings.secret_key, settings.access_token_ttl_seconds)
    token = issuer.issue(subject=user.id)

    return DevLoginResponse(
        access_token=token,
        expires_in=settings.access_token_ttl_seconds,
        user_id=user.id,
        organization_id=user.organization_id,
    )
