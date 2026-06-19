"""Workflow run creation and retrieval endpoints."""

import uuid

import redis
from clickhouse_connect.driver.client import Client
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.clickhouse import get_clickhouse
from app.db.postgres import get_db
from app.db.redis import get_redis
from app.schemas.run import WorkflowRunCreate, WorkflowRunResponse
from app.schemas.trace import TraceEventResponse
from app.services import run_service, trace_service
from app.services.exceptions import (
    RunNotFoundError,
    WorkflowNotFoundError,
    WorkflowNotReadyError,
)

router = APIRouter(tags=["runs"])


@router.post(
    "/workflows/{workflow_id}/run",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_run(
    workflow_id: uuid.UUID,
    payload: WorkflowRunCreate,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> WorkflowRunResponse:
    try:
        return run_service.create_run(db, redis_client, workflow_id, payload)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    except WorkflowNotReadyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow has no saved version to run",
        )


@router.get("/runs", response_model=list[WorkflowRunResponse])
def list_runs(
    workflow_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[WorkflowRunResponse]:
    return run_service.list_runs(db, workflow_id=workflow_id)


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> WorkflowRunResponse:
    try:
        return run_service.get_run(db, run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")


@router.get("/runs/{run_id}/trace", response_model=list[TraceEventResponse])
def get_run_trace(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    clickhouse_client: Client = Depends(get_clickhouse),
) -> list[TraceEventResponse]:
    try:
        return trace_service.get_run_trace(db, clickhouse_client, run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
