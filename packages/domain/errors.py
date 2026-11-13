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
    """An upload's media type is not in the configured allowlist, or its content's
    magic-byte signature does not match what it claims to be."""


class AssetNotReadyError(InvalidStateError):
    """An asset exists but cannot be used yet (still quarantined, or scanned infected)."""


class ConsentRequiredError(TenantAccessViolation):
    """A gated action was attempted without the specific active consent purpose it
    requires (D4, TFD-CHR-002.2/TFD-PHY-006/TFD-CNS-005). The message is always
    ``"consent_required: <purpose>"`` so callers can parse the missing purpose out of
    ``detail`` directly, matching the acceptance criteria's literal wording."""

    def __init__(self, purpose: str):
        self.purpose = purpose
        super().__init__(f"consent_required: {purpose}")


class PolicyPendingError(TenantAccessViolation):
    """Performer or consent-record creation is blocked because DEC-007 (retention) and/or
    DEC-012 (consent template) have not yet been approved (D4, AT-CNS-002.2). No
    likeness, body or voice data may be stored before Legal closes both."""

    def __init__(self):
        super().__init__("policy_pending")
