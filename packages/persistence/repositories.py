"""SQLAlchemy repositories enforcing tenant and project scoping."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from packages.domain.invariants import TenantAccessViolation, VersionConflictError
from packages.persistence.models import (
    ApprovalRequestModel,
    AssetModel,
    AuditEventModel,
    EntityCandidateModel,
    EntityModel,
    OrganizationModel,
    OutboxTaskModel,
    ProjectModel,
    ProjectVersionModel,
    SceneCandidateModel,
    SceneModel,
    UserModel,
    WorkflowRunModel,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_organization(self, name: str, slug: str) -> OrganizationModel:
        org = OrganizationModel(name=name, slug=slug)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def create_user(self, org_id: str, email: str, full_name: str, role: str = "creator") -> UserModel:
        user = UserModel(organization_id=org_id, email=email, full_name=full_name, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_project(
        self,
        org_id: str,
        actor_id: str,
        title: str,
        logline: Optional[str] = None,
        genre: Optional[str] = None,
    ) -> ProjectModel:
        project = ProjectModel(
            organization_id=org_id,
            created_by=actor_id,
            title=title,
            logline=logline,
            genre=genre,
            current_version=1,
            status="active",
        )
        self.db.add(project)
        self.db.flush()

        # Create initial Version 1 snapshot
        initial_version = ProjectVersionModel(
            project_id=project.id,
            version_number=1,
            branch_name="main",
            commit_message="Initial project creation",
            committed_by=actor_id,
            snapshot_data={"title": title, "logline": logline, "genre": genre},
        )
        self.db.add(initial_version)

        # Audit event
        audit = AuditEventModel(
            project_id=project.id,
            organization_id=org_id,
            actor_id=actor_id,
            action="project.created",
            target_type="project",
            target_id=project.id,
            details={"title": title, "genre": genre},
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project_scoped(self, project_id: str, org_id: str) -> ProjectModel:
        stmt = select(ProjectModel).where(
            and_(ProjectModel.id == project_id, ProjectModel.organization_id == org_id)
        )
        project = self.db.scalars(stmt).first()
        if not project:
            raise TenantAccessViolation(f"Project '{project_id}' not found or access denied for org '{org_id}'.")
        return project

    def list_projects_for_org(self, org_id: str) -> List[ProjectModel]:
        stmt = select(ProjectModel).where(ProjectModel.organization_id == org_id).order_by(ProjectModel.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def commit_new_version(
        self,
        project_id: str,
        org_id: str,
        actor_id: str,
        expected_version: int,
        commit_message: str,
        snapshot_data: Dict[str, Any],
    ) -> ProjectVersionModel:
        project = self.get_project_scoped(project_id, org_id)
        if project.current_version != expected_version:
            raise VersionConflictError(
                f"Version conflict on project '{project_id}': expected {expected_version}, found {project.current_version}."
            )

        new_version_num = project.current_version + 1
        project.current_version = new_version_num
        project.updated_at = utc_now()

        version_record = ProjectVersionModel(
            project_id=project_id,
            version_number=new_version_num,
            branch_name="main",
            commit_message=commit_message,
            committed_by=actor_id,
            snapshot_data=snapshot_data,
        )
        self.db.add(version_record)

        audit = AuditEventModel(
            project_id=project_id,
            organization_id=org_id,
            actor_id=actor_id,
            action="project.version_committed",
            target_type="project_version",
            target_id=version_record.id,
            details={"version_number": new_version_num, "commit_message": commit_message},
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(version_record)
        return version_record


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_asset(
        self,
        project_id: str,
        org_id: str,
        actor_id: str,
        filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str,
        storage_path: str,
        asset_type: str = "script",
        is_original: bool = True,
        parent_asset_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssetModel:
        asset = AssetModel(
            project_id=project_id,
            organization_id=org_id,
            uploaded_by=actor_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            storage_path=storage_path,
            asset_type=asset_type,
            is_original=is_original,
            parent_asset_id=parent_asset_id,
            asset_metadata=metadata or {},
        )
        self.db.add(asset)

        audit = AuditEventModel(
            project_id=project_id,
            organization_id=org_id,
            actor_id=actor_id,
            action="asset.uploaded",
            target_type="asset",
            target_id=asset.id,
            details={"filename": filename, "checksum": checksum_sha256, "size_bytes": size_bytes},
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(asset)
        return asset

    def get_asset_scoped(self, asset_id: str, project_id: str, org_id: str) -> AssetModel:
        stmt = select(AssetModel).where(
            and_(
                AssetModel.id == asset_id,
                AssetModel.project_id == project_id,
                AssetModel.organization_id == org_id,
            )
        )
        asset = self.db.scalars(stmt).first()
        if not asset:
            raise TenantAccessViolation(f"Asset '{asset_id}' not found or access denied.")
        return asset

    def list_assets_for_project(self, project_id: str, org_id: str) -> List[AssetModel]:
        stmt = select(AssetModel).where(
            and_(AssetModel.project_id == project_id, AssetModel.organization_id == org_id)
        ).order_by(AssetModel.created_at.desc())
        return list(self.db.scalars(stmt).all())


class WorkflowRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(
        self,
        graph_id: str,
        graph_version: str,
        project_id: str,
        org_id: str,
        actor_id: str,
        expected_project_version: int,
        input_asset_ids: List[str],
    ) -> WorkflowRunModel:
        run = WorkflowRunModel(
            graph_id=graph_id,
            graph_version=graph_version,
            project_id=project_id,
            organization_id=org_id,
            actor_id=actor_id,
            expected_project_version=expected_project_version,
            status="queued",
            input_asset_ids=input_asset_ids,
        )
        self.db.add(run)
        self.db.flush()

        # Enqueue durable outbox task
        outbox = OutboxTaskModel(
            workflow_run_id=run.id,
            task_type=f"execute_{graph_id}",
            payload={"run_id": run.id, "project_id": project_id, "org_id": org_id},
            status="pending",
        )
        self.db.add(outbox)

        audit = AuditEventModel(
            project_id=project_id,
            organization_id=org_id,
            actor_id=actor_id,
            action="workflow.run.queued",
            target_type="workflow_run",
            target_id=run.id,
            details={"graph_id": graph_id, "graph_version": graph_version},
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run_scoped(self, run_id: str, org_id: str) -> WorkflowRunModel:
        stmt = select(WorkflowRunModel).where(
            and_(WorkflowRunModel.id == run_id, WorkflowRunModel.organization_id == org_id)
        )
        run = self.db.scalars(stmt).first()
        if not run:
            raise TenantAccessViolation(f"Workflow run '{run_id}' not found or access denied.")
        return run

    def update_status(
        self,
        run_id: str,
        status: str,
        output_refs: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        run = self.db.get(WorkflowRunModel, run_id)
        if run:
            run.status = status
            if output_refs:
                run.output_refs = output_refs
            if error_message:
                run.error_message = error_message
            run.updated_at = utc_now()
            self.db.commit()


class ApprovalRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_approval_request(
        self,
        workflow_run_id: str,
        project_id: str,
        org_id: str,
        scope: str,
        candidate_summary: Dict[str, Any],
    ) -> ApprovalRequestModel:
        approval = ApprovalRequestModel(
            workflow_run_id=workflow_run_id,
            project_id=project_id,
            organization_id=org_id,
            scope=scope,
            candidate_summary=candidate_summary,
            status="pending",
        )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def get_approval_scoped(self, approval_id: str, org_id: str) -> ApprovalRequestModel:
        stmt = select(ApprovalRequestModel).where(
            and_(ApprovalRequestModel.id == approval_id, ApprovalRequestModel.organization_id == org_id)
        )
        approval = self.db.scalars(stmt).first()
        if not approval:
            raise TenantAccessViolation(f"Approval '{approval_id}' not found or access denied.")
        return approval

    def record_decision(
        self,
        approval_id: str,
        org_id: str,
        actor_id: str,
        decision: str,
        decision_notes: Optional[str] = None,
    ) -> ApprovalRequestModel:
        approval = self.get_approval_scoped(approval_id, org_id)
        approval.status = "decided"
        approval.decision = decision
        approval.decision_notes = decision_notes
        approval.decided_by = actor_id
        approval.decided_at = utc_now()

        audit = AuditEventModel(
            project_id=approval.project_id,
            organization_id=org_id,
            actor_id=actor_id,
            action=f"approval.{decision}",
            target_type="approval_request",
            target_id=approval_id,
            details={"decision": decision, "notes": decision_notes},
        )
        self.db.add(audit)

        self.db.commit()
        self.db.refresh(approval)
        return approval


class CandidateRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_scene_candidates(self, candidates: List[SceneCandidateModel]) -> None:
        self.db.add_all(candidates)
        self.db.commit()

    def save_entity_candidates(self, candidates: List[EntityCandidateModel]) -> None:
        self.db.add_all(candidates)
        self.db.commit()

    def list_scene_candidates(self, run_id: str, project_id: str) -> List[SceneCandidateModel]:
        stmt = select(SceneCandidateModel).where(
            and_(SceneCandidateModel.workflow_run_id == run_id, SceneCandidateModel.project_id == project_id)
        ).order_by(SceneCandidateModel.scene_number.asc())
        return list(self.db.scalars(stmt).all())

    def list_entity_candidates(self, run_id: str, project_id: str) -> List[EntityCandidateModel]:
        stmt = select(EntityCandidateModel).where(
            and_(EntityCandidateModel.workflow_run_id == run_id, EntityCandidateModel.project_id == project_id)
        ).order_by(EntityCandidateModel.category.asc(), EntityCandidateModel.name.asc())
        return list(self.db.scalars(stmt).all())

    def commit_approved_candidates(
        self,
        run_id: str,
        project_id: str,
        new_project_version: int,
    ) -> None:
        # Commit scene candidates to canonical scenes table
        scene_candidates = self.list_scene_candidates(run_id, project_id)
        for sc in scene_candidates:
            if sc.status in ("proposed", "approved"):
                sc.status = "approved"
                scene = SceneModel(
                    project_id=project_id,
                    scene_number=sc.scene_number,
                    heading=sc.heading,
                    setting=sc.setting,
                    location_name=sc.location_name,
                    time_of_day=sc.time_of_day,
                    summary=sc.summary,
                    source_locator=sc.source_locator,
                    characters_present=sc.characters_present,
                    project_version=new_project_version,
                )
                self.db.add(scene)

        # Commit entity candidates to canonical entities table
        entity_candidates = self.list_entity_candidates(run_id, project_id)
        for ec in entity_candidates:
            if ec.status in ("proposed", "approved"):
                ec.status = "approved"
                entity = EntityModel(
                    project_id=project_id,
                    name=ec.name,
                    category=ec.category,
                    description=ec.description,
                    source_locator=ec.source_locator,
                    project_version=new_project_version,
                )
                self.db.add(entity)

        self.db.commit()
