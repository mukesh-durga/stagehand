"""Business logic for creating and reading workflow runs.

This milestone only creates a run record and enqueues a job. The worker
(Milestone 6) consumes the job and executes the workflow.
"""

import json
import uuid

import redis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models.run import WorkflowRun
from app.db.redis import RUN_QUEUE_KEY
from app.db.repositories.run_repository import RunRepository
from app.db.repositories.workflow_repository import WorkflowRepository
from app.schemas.run import RunConfig, WorkflowRunCreate, WorkflowRunResponse
from app.services.exceptions import (
    RunNotFoundError,
    WorkflowNotFoundError,
    WorkflowNotReadyError,
)


def _to_response(run: WorkflowRun) -> WorkflowRunResponse:
    return WorkflowRunResponse(
        id=run.id,
        workflow_id=run.workflow_id,
        workflow_version_id=run.workflow_version_id,
        status=run.status,
        input=run.input_json or {},
        output=run.output_json,
        error_message=run.error_message,
        total_latency_ms=run.total_latency_ms,
        total_input_tokens=run.total_input_tokens,
        total_output_tokens=run.total_output_tokens,
        estimated_cost_usd=(
            float(run.estimated_cost_usd) if run.estimated_cost_usd is not None else None
        ),
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _resolve_run_config(run_config: RunConfig | None) -> dict[str, float | int]:
    settings = get_settings()
    rc = run_config or RunConfig()
    return {
        "max_steps": rc.max_steps if rc.max_steps is not None else settings.default_max_steps,
        "max_cost_usd": (
            rc.max_cost_usd if rc.max_cost_usd is not None else settings.default_max_cost_usd
        ),
        "max_runtime_seconds": (
            rc.max_runtime_seconds
            if rc.max_runtime_seconds is not None
            else settings.default_max_runtime_seconds
        ),
    }


def create_run(
    db: Session,
    redis_client: redis.Redis,
    workflow_id: uuid.UUID,
    data: WorkflowRunCreate,
) -> WorkflowRunResponse:
    workflow = WorkflowRepository(db).get(workflow_id)
    if workflow is None:
        raise WorkflowNotFoundError(str(workflow_id))
    if workflow.current_version_id is None:
        raise WorkflowNotReadyError(str(workflow_id))

    run = WorkflowRun(
        workflow_id=workflow.id,
        workflow_version_id=workflow.current_version_id,
        status="queued",
        input_json=data.input or {},
    )
    RunRepository(db).add(run)
    db.commit()
    db.refresh(run)

    run_config = _resolve_run_config(data.run_config)
    job = {
        "run_id": str(run.id),
        "workflow_id": str(run.workflow_id),
        "workflow_version_id": str(run.workflow_version_id),
        "input": run.input_json or {},
        "run_config": run_config,
        "created_at": run.created_at.isoformat(),
    }
    redis_client.rpush(RUN_QUEUE_KEY, json.dumps(job))

    return _to_response(run)


def get_run(db: Session, run_id: uuid.UUID) -> WorkflowRunResponse:
    run = RunRepository(db).get(run_id)
    if run is None:
        raise RunNotFoundError(str(run_id))
    return _to_response(run)


def list_runs(
    db: Session, workflow_id: uuid.UUID | None = None, limit: int = 50
) -> list[WorkflowRunResponse]:
    runs = RunRepository(db).list_recent(workflow_id=workflow_id, limit=limit)
    return [_to_response(r) for r in runs]
