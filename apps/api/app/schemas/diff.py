"""Schemas for comparing two runs (Milestone 13)."""

from pydantic import BaseModel

from app.schemas.run import WorkflowRunResponse


class RunDiffSummary(BaseModel):
    status_changed: bool
    workflow_version_changed: bool
    latency_delta_ms: int
    input_tokens_delta: int
    output_tokens_delta: int
    cost_delta: float
    error_changed: bool
    model_changed: bool
    tool_changed: bool
    retry_count_delta: int
    fallback_changed: bool


class NodeDiff(BaseModel):
    node_id: str
    status_a: str
    status_b: str
    status_changed: bool
    model_a: str
    model_b: str
    model_changed: bool
    tool_a: str
    tool_b: str
    tool_changed: bool
    latency_a_ms: int
    latency_b_ms: int
    latency_delta_ms: int
    input_tokens_a: int
    input_tokens_b: int
    output_tokens_a: int
    output_tokens_b: int
    cost_a: float
    cost_b: float
    cost_delta: float
    retry_count_a: int
    retry_count_b: int
    fallback_used_a: bool
    fallback_used_b: bool
    error_a: str
    error_b: str
    output_summary_a: str
    output_summary_b: str


class EventDiff(BaseModel):
    event_type: str
    node_id: str
    count_a: int
    count_b: int
    changed: bool
    details: str = ""


class OutputDiff(BaseModel):
    changed: bool
    output_a_summary: str
    output_b_summary: str


class RunDiffResponse(BaseModel):
    run_a: WorkflowRunResponse
    run_b: WorkflowRunResponse
    summary: RunDiffSummary
    node_diffs: list[NodeDiff]
    event_diffs: list[EventDiff]
    output_diff: OutputDiff
