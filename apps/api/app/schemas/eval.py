"""Pydantic schemas for the eval harness."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

EVAL_TYPES = (
    "exact_match",
    "json_schema",
    "tool_usage",
    "latency",
    "cost",
    "llm_as_judge",
)

DEFAULT_EVAL_TYPES = ["latency", "cost", "llm_as_judge"]


class EvalRequest(BaseModel):
    eval_types: list[str] | None = None
    expected_output: Any | None = None
    expected_schema: dict[str, Any] | None = None
    expected_tools: list[str] | None = None
    max_latency_ms: int | None = None
    max_cost_usd: float | None = None
    judge_prompt: str | None = None


class EvalResultResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_version_id: uuid.UUID
    eval_type: str
    success_score: float
    tool_correctness_score: float | None
    format_score: float | None
    quality_score: float | None
    cost_score: float | None
    latency_score: float | None
    passed: bool
    feedback: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
