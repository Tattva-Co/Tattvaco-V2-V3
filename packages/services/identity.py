"""Actor identity resolution (OPEN_DECISIONS DEC-002: header-based identity boundary).

Until an authentication provider is selected, the caller identifies itself with an
``X-Actor-ID`` header naming an existing user. The actor's organization is always read
from the database, never trusted from the request. In development/test environments a
missing header falls back to the bootstrap "default studio" user so the local UI works
without login; in staging/production a missing header is rejected.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from packages.domain.errors import DomainInvariantError
from packages.persistence.repositories import UserRepository


class AuthenticationError(DomainInvariantError):
    """No valid actor identity was supplied."""


@dataclass(frozen=True)
class ActorContext:
    user_id: str
    org_id: str


class IdentityService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def resolve(self, actor_id: str | None, *, allow_dev_fallback: bool) -> ActorContext:
        if actor_id:
            user = self.users.get(actor_id)
            if user is None:
                raise AuthenticationError("Unknown actor.")
            return ActorContext(user_id=user.id, org_id=user.organization_id)

        if not allow_dev_fallback:
            raise AuthenticationError("Missing X-Actor-ID header.")

        user = self.users.get_or_create_default_actor()
        self.db.commit()
        return ActorContext(user_id=user.id, org_id=user.organization_id)
