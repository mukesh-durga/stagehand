"""Database access for workflows and workflow versions."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.workflow import Workflow, WorkflowVersion


class WorkflowRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- workflows ---
    def add(self, obj: Workflow | WorkflowVersion) -> None:
        self.db.add(obj)

    def get(self, workflow_id: uuid.UUID) -> Workflow | None:
        return self.db.get(Workflow, workflow_id)

    def list_all(self) -> list[Workflow]:
        stmt = select(Workflow).order_by(Workflow.created_at.desc())
        return list(self.db.scalars(stmt))

    def delete(self, workflow: Workflow) -> None:
        self.db.delete(workflow)

    # --- versions ---
    def get_version(self, version_id: uuid.UUID) -> WorkflowVersion | None:
        return self.db.get(WorkflowVersion, version_id)

    def list_versions(self, workflow_id: uuid.UUID) -> list[WorkflowVersion]:
        stmt = (
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .order_by(WorkflowVersion.version_number)
        )
        return list(self.db.scalars(stmt))

    def max_version_number(self, workflow_id: uuid.UUID) -> int | None:
        stmt = select(func.max(WorkflowVersion.version_number)).where(
            WorkflowVersion.workflow_id == workflow_id
        )
        return self.db.scalar(stmt)
