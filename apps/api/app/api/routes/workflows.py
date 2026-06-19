"""Workflow CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
    WorkflowVersionResponse,
)
from app.services import workflow_service
from app.services.exceptions import GraphValidationError, WorkflowNotFoundError

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)) -> WorkflowResponse:
    try:
        return workflow_service.create_workflow(db, payload)
    except GraphValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=list[WorkflowResponse])
def list_workflows(db: Session = Depends(get_db)) -> list[WorkflowResponse]:
    return workflow_service.list_workflows(db)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)) -> WorkflowResponse:
    try:
        return workflow_service.get_workflow(db, workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: uuid.UUID, payload: WorkflowUpdate, db: Session = Depends(get_db)
) -> WorkflowResponse:
    try:
        return workflow_service.update_workflow(db, workflow_id, payload)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    except GraphValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    try:
        workflow_service.delete_workflow(db, workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{workflow_id}/versions", response_model=list[WorkflowVersionResponse])
def list_workflow_versions(
    workflow_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[WorkflowVersionResponse]:
    try:
        return workflow_service.list_workflow_versions(db, workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
