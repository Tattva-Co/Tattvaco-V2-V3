"""Actor identity resolution (ADR-003).

Two paths, selected by environment, never by a client-supplied flag:

- ``environment == "test"``: the caller names an existing user via the ``X-Actor-ID``
  header. No token is required. This keeps the test suite simple and fast; it is not
  reachable in any other environment (enforced in ``apps/api/dependencies.py``).
- every other environment: the caller presents a verified :class:`~packages.services.auth.
  Principal` (a signed, non-expired bearer token already checked by an ``AuthProvider``).
  This module only maps that principal to a ``users`` row — it never trusts a raw ID
  supplied by the request and never silently manufactures an identity.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from packages.domain.errors import AuthenticationError
from packages.persistence.repositories import UserRepository
from packages.services.auth import Principal

__all__ = ["AuthenticationError", "ActorContext", "IdentityService"]


@dataclass(frozen=True)
class ActorContext:
    user_id: str
    org_id: str


class IdentityService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def resolve_header(self, actor_id: str | None) -> ActorContext:
        """Test-only path: ``X-Actor-ID`` names an existing user directly."""
        if not actor_id:
            raise AuthenticationError("Missing X-Actor-ID header.")
        user = self.users.get(actor_id)
        if user is None:
            raise AuthenticationError("Unknown actor.")
        return ActorContext(user_id=user.id, org_id=user.organization_id)

    def resolve_principal(self, principal: Principal) -> ActorContext:
        """Map a verified token's identity to a ``users`` row.

        Dev tokens (issuer ``tattva-dev``) carry the user's own id as ``sub``, since
        there is no external identity to look up in that mode. Every other issuer is
        treated as an OIDC provider and resolved through the ``(idp_issuer, idp_subject)``
        link created when the user was provisioned.
        """
        if principal.issuer == "tattva-dev":
            user = self.users.get(principal.subject)
        else:
            user = self.users.get_by_idp_identity(principal.issuer, principal.subject)
        if user is None:
            raise AuthenticationError("Token does not correspond to a known user.")
        return ActorContext(user_id=user.id, org_id=user.organization_id)
