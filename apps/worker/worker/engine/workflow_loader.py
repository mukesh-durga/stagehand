"""Loading workflow versions from PostgreSQL."""

import uuid

from sqlalchemy.orm import Session

from worker.engine.errors import WorkflowLoadError
from worker.models import WorkflowVersion


def load_workflow_version(
    db: Session, version_id: uuid.UUID | str
) -> WorkflowVersion:
    if isinstance(version_id, str):
        version_id = uuid.UUID(version_id)
    version = db.get(WorkflowVersion, version_id)
    if version is None:
        raise WorkflowLoadError(f"Workflow version {version_id} not found.")
    return version
