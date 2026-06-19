"""Business logic for workflow CRUD and versioning."""

import uuid

from sqlalchemy.orm import Session

from app.db.models.workflow import Workflow, WorkflowVersion
from app.db.repositories.workflow_repository import WorkflowRepository
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
    WorkflowVersionResponse,
)
from app.services.exceptions import WorkflowNotFoundError
from app.services.graph_validation import validate_graph


def _to_response(
    workflow: Workflow, version: WorkflowVersion | None
) -> WorkflowResponse:
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        current_version_id=workflow.current_version_id,
        current_version_number=version.version_number if version else None,
        graph=version.graph_json if version else {"nodes": [], "edges": []},
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def _current_version(
    repo: WorkflowRepository, workflow: Workflow
) -> WorkflowVersion | None:
    if workflow.current_version_id is None:
        return None
    return repo.get_version(workflow.current_version_id)


def create_workflow(db: Session, data: WorkflowCreate) -> WorkflowResponse:
    validate_graph(data.graph)
    repo = WorkflowRepository(db)

    workflow = Workflow(name=data.name, description=data.description)
    repo.add(workflow)
    db.flush()  # assign workflow.id

    version = WorkflowVersion(
        workflow_id=workflow.id,
        version_number=1,
        graph_json=data.graph.model_dump(mode="json"),
    )
    repo.add(version)
    db.flush()  # assign version.id

    workflow.current_version_id = version.id
    db.commit()
    db.refresh(workflow)
    db.refresh(version)
    return _to_response(workflow, version)


def list_workflows(db: Session) -> list[WorkflowResponse]:
    repo = WorkflowRepository(db)
    return [_to_response(wf, _current_version(repo, wf)) for wf in repo.list_all()]


def get_workflow(db: Session, workflow_id: uuid.UUID) -> WorkflowResponse:
    repo = WorkflowRepository(db)
    workflow = repo.get(workflow_id)
    if workflow is None:
        raise WorkflowNotFoundError(str(workflow_id))
    return _to_response(workflow, _current_version(repo, workflow))


def update_workflow(
    db: Session, workflow_id: uuid.UUID, data: WorkflowUpdate
) -> WorkflowResponse:
    repo = WorkflowRepository(db)
    workflow = repo.get(workflow_id)
    if workflow is None:
        raise WorkflowNotFoundError(str(workflow_id))

    if data.name is not None:
        workflow.name = data.name
    if data.description is not None:
        workflow.description = data.description

    version = _current_version(repo, workflow)

    if data.graph is not None:
        validate_graph(data.graph)
        next_number = (repo.max_version_number(workflow_id) or 0) + 1
        version = WorkflowVersion(
            workflow_id=workflow.id,
            version_number=next_number,
            graph_json=data.graph.model_dump(mode="json"),
        )
        repo.add(version)
        db.flush()
        workflow.current_version_id = version.id

    db.commit()
    db.refresh(workflow)
    if version is not None:
        db.refresh(version)
    return _to_response(workflow, version)


def delete_workflow(db: Session, workflow_id: uuid.UUID) -> None:
    repo = WorkflowRepository(db)
    workflow = repo.get(workflow_id)
    if workflow is None:
        raise WorkflowNotFoundError(str(workflow_id))
    repo.delete(workflow)
    db.commit()


def list_workflow_versions(
    db: Session, workflow_id: uuid.UUID
) -> list[WorkflowVersionResponse]:
    repo = WorkflowRepository(db)
    workflow = repo.get(workflow_id)
    if workflow is None:
        raise WorkflowNotFoundError(str(workflow_id))
    return [
        WorkflowVersionResponse(
            id=v.id,
            workflow_id=v.workflow_id,
            version_number=v.version_number,
            graph=v.graph_json,
            created_at=v.created_at,
        )
        for v in repo.list_versions(workflow_id)
    ]
