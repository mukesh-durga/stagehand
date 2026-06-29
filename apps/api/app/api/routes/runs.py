"""Workflow run creation and retrieval endpoints."""

import uuid

import redis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_trace_store
from app.db.postgres import get_db
from app.db.redis import get_redis
from app.db.trace_store import TraceStore
from app.schemas.diff import RunDiffResponse
from app.schemas.eval import EvalRequest, EvalResultResponse
from app.schemas.run import WorkflowRunCreate, WorkflowRunResponse
from app.schemas.trace import TraceEventResponse
from app.services import diff_service, eval_service, run_service, trace_service
from app.services.exceptions import (
    RunNotEvaluatableError,
    RunNotFoundError,
    UnknownEvalTypeError,
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> WorkflowRunResponse:
    try:
        return run_service.create_run(
            db, redis_client, workflow_id, payload, background_tasks=background_tasks
        )
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


@router.post(
    "/runs/{run_id}/replay",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def replay_run(
    run_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> WorkflowRunResponse:
    try:
        return run_service.replay_run(
            db, redis_client, run_id, background_tasks=background_tasks
        )
    except RunNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")


@router.get("/runs/{run_id}/replays", response_model=list[WorkflowRunResponse])
def list_replays(
    run_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[WorkflowRunResponse]:
    return run_service.list_replays(db, run_id)


@router.get(
    "/runs/{run_id}/diff/{other_run_id}", response_model=RunDiffResponse
)
def diff_runs(
    run_id: uuid.UUID,
    other_run_id: uuid.UUID,
    db: Session = Depends(get_db),
    store: TraceStore = Depends(get_trace_store),
) -> RunDiffResponse:
    try:
        return diff_service.diff_runs(db, store, run_id, other_run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")


@router.post(
    "/runs/{run_id}/eval",
    response_model=list[EvalResultResponse],
    status_code=status.HTTP_201_CREATED,
)
def run_eval(
    run_id: uuid.UUID,
    payload: EvalRequest | None = None,
    db: Session = Depends(get_db),
    store: TraceStore = Depends(get_trace_store),
) -> list[EvalResultResponse]:
    try:
        return eval_service.run_eval(db, store, run_id, payload or EvalRequest())
    except RunNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    except RunNotEvaluatableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run must be completed or failed to evaluate",
        )
    except UnknownEvalTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown eval type: {exc}"
        )


@router.get("/runs/{run_id}/evals", response_model=list[EvalResultResponse])
def list_evals(
    run_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[EvalResultResponse]:
    return eval_service.list_evals(db, run_id)


@router.get("/runs/{run_id}/trace", response_model=list[TraceEventResponse])
def get_run_trace(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    store: TraceStore = Depends(get_trace_store),
) -> list[TraceEventResponse]:
    try:
        return trace_service.get_run_trace(db, store, run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
