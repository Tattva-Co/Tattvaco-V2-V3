"""Domain error hierarchy.

Services raise these; the API layer maps them to HTTP status codes in one place
(``apps/api/errors.py``). Domain code never raises HTTP exceptions.
"""


class DomainInvariantError(Exception):
    """Base class: a business rule or core invariant was violated."""


class AuthenticationError(DomainInvariantError):
    """The caller did not present a valid, verifiable identity."""


class NotFoundError(DomainInvariantError):
    """The requested object does not exist (or is not visible to the actor)."""


class TenantAccessViolation(DomainInvariantError):
    """Cross-tenant or cross-project access was attempted."""


class VersionConflictError(DomainInvariantError):
    """An operation was based on a stale project version."""


class InvalidStateError(DomainInvariantError):
    """The object is not in a state that allows this operation."""


class ValidationFailure(DomainInvariantError):
    """Input was well-formed but violates a business rule."""


class PayloadTooLargeError(ValidationFailure):
    """An upload exceeds the configured size limit."""


class UnsupportedMediaTypeError(ValidationFailure):
    """An upload's media type is not in the configured allowlist."""
