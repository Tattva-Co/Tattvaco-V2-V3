"""Append-only body measurement observations with full provenance (D4, TFD-PHY-001/002/
003/004/006).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import List

from sqlalchemy.orm import Session

from packages.domain.enums import AuditAction, CaptureMethod, MeasurementStatus
from packages.domain.errors import InvalidStateError, ValidationFailure
from packages.persistence.models import BodyMeasurementModel
from packages.persistence.repositories import (
    AssetRepository,
    AuditRepository,
    BodyMeasurementRepository,
    ProjectRepository,
)
from packages.services.authz import AuthzService
from packages.services.consent import ConsentService
from packages.services.identity import ActorContext

#: AT-PHY-004.1: an AI estimate from a single photograph is not anthropometric ground
#: truth -- capped low and barred from ever being verified without an independent
#: measured/scanned observation.
_AI_ESTIMATE_CONFIDENCE_CAP = 0.5


class MeasurementService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.measurements = BodyMeasurementRepository(db)
        self.assets = AssetRepository(db)
        self.authz = AuthzService(db)
        self.consent = ConsentService(db)
        self.audit = AuditRepository(db)

    def save_measurement(
        self,
        actor: ActorContext,
        project_id: str,
        *,
        subject_type: str,
        subject_id: str,
        measurement_key: str,
        value: float,
        unit: str | None,
        capture_method: str,
        confidence: float | None = None,
        source_asset_id: str | None = None,
        capture_device_or_tool: str | None = None,
        notes: str | None = None,
    ) -> BodyMeasurementModel:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        if not unit:
            raise ValidationFailure("unit is required.")  # AT-PHY-002.1
        if source_asset_id:
            self.assets.get_for_project(source_asset_id, project.id)

        if subject_type == "performer":
            # AT-PHY-006.1: re-derived from active consent rows every time, never
            # trusted from client-supplied state.
            self.consent.require(subject_id, "reference_storage", project.id)

        if capture_method == CaptureMethod.AI_ESTIMATE.value:
            status = MeasurementStatus.ESTIMATED.value
            confidence = min(confidence if confidence is not None else _AI_ESTIMATE_CONFIDENCE_CAP, _AI_ESTIMATE_CONFIDENCE_CAP)
        else:
            status = MeasurementStatus.MEASURED.value

        measurement = self.measurements.add(
            BodyMeasurementModel(
                organization_id=project.organization_id,
                project_id=project.id,
                subject_type=subject_type,
                subject_id=subject_id,
                measurement_key=measurement_key,
                value=value,
                unit=unit,
                status=status,
                confidence=confidence,
                capture_method=capture_method,
                version=self.measurements.next_version(subject_type, subject_id, measurement_key),
                capture_device_or_tool=capture_device_or_tool,
                source_asset_id=source_asset_id,
                captured_by=actor.user_id,
                notes=notes,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.MEASUREMENT_RECORDED,
            target_type="body_measurement",
            target_id=measurement.id,
            details={"measurement_key": measurement_key, "status": status, "capture_method": capture_method},
        )
        self.db.commit()
        return measurement

    def correct_measurement(
        self, actor: ActorContext, project_id: str, measurement_id: str, *, value: float, unit: str | None = None, notes: str | None = None
    ) -> BodyMeasurementModel:
        """AT-PHY-003.1: the prior row is marked superseded, never deleted or
        overwritten -- both remain visible in history."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        previous = self.measurements.get_scoped(measurement_id, project.id)
        previous.status = MeasurementStatus.SUPERSEDED.value

        corrected = self.measurements.add(
            BodyMeasurementModel(
                organization_id=project.organization_id,
                project_id=project.id,
                subject_type=previous.subject_type,
                subject_id=previous.subject_id,
                measurement_key=previous.measurement_key,
                value=value,
                unit=unit or previous.unit,
                status=MeasurementStatus.MEASURED.value,
                confidence=None,
                capture_method=CaptureMethod.MANUAL_CORRECTION.value,
                version=previous.version + 1,
                source_asset_id=previous.source_asset_id,
                captured_by=actor.user_id,
                supersedes_id=previous.id,
                notes=notes,
            )
        )
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.MEASUREMENT_CORRECTED,
            target_type="body_measurement",
            target_id=corrected.id,
            details={"supersedes_id": previous.id},
        )
        self.db.commit()
        return corrected

    def verify_measurement(self, actor: ActorContext, project_id: str, measurement_id: str) -> BodyMeasurementModel:
        """AT-PHY-004.1/004.2: an AI estimate can never become verified without an
        independent calibrated/measured observation superseding it first; a verifier
        must also differ from whoever captured the row (architecture doc §3.4)."""
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "canon.propose", project)
        measurement = self.measurements.get_scoped(measurement_id, project.id)

        if measurement.capture_method == CaptureMethod.AI_ESTIMATE.value:
            raise ValidationFailure("calibrated_capture_required")
        if measurement.captured_by == actor.user_id:
            raise InvalidStateError("A verifier must differ from the capturer.")

        measurement.status = MeasurementStatus.VERIFIED.value
        measurement.verified_by = actor.user_id
        measurement.verified_at = datetime.now(UTC)
        self.audit.record(
            project_id=project.id,
            organization_id=project.organization_id,
            actor_id=actor.user_id,
            action=AuditAction.MEASUREMENT_VERIFIED,
            target_type="body_measurement",
            target_id=measurement.id,
            details={},
        )
        self.db.commit()
        return measurement

    def history(self, actor: ActorContext, project_id: str, subject_type: str, subject_id: str) -> List[BodyMeasurementModel]:
        project = self.projects.get_scoped(project_id, actor.org_id)
        self.authz.require(actor, "project.read", project)
        return self.measurements.history_for_subject(project.id, subject_type, subject_id)
