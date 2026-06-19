"""Pydantic schemas for workflow runs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunConfig(BaseModel):
    """Optional per-run limits. Unset fields fall back to settings defaults."""

    max_steps: int | None = None
    max_cost_usd: float | None = None
    max_runtime_seconds: int | None = None


class WorkflowRunCreate(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    run_config: RunConfig | None = None


class WorkflowRunResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_version_id: uuid.UUID
    status: str
    input: dict[str, Any]
    output: dict[str, Any] | None
    error_message: str | None
    total_latency_ms: int | None
    total_input_tokens: int | None
    total_output_tokens: int | None
    estimated_cost_usd: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
