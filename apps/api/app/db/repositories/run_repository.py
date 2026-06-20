"""Database access for workflow runs."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.run import WorkflowRun


class RunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, run: WorkflowRun) -> None:
        self.db.add(run)

    def get(self, run_id: uuid.UUID) -> WorkflowRun | None:
        return self.db.get(WorkflowRun, run_id)

    def list_recent(
        self, workflow_id: uuid.UUID | None = None, limit: int = 50
    ) -> list[WorkflowRun]:
        stmt = select(WorkflowRun)
        if workflow_id is not None:
            stmt = stmt.where(WorkflowRun.workflow_id == workflow_id)
        stmt = stmt.order_by(WorkflowRun.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def list_replays(self, run_id: uuid.UUID) -> list[WorkflowRun]:
        stmt = (
            select(WorkflowRun)
            .where(WorkflowRun.replay_of_run_id == run_id)
            .order_by(WorkflowRun.created_at.desc())
        )
        return list(self.db.scalars(stmt))
