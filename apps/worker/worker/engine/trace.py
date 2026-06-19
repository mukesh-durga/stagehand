"""TraceEvent schema and trace Redis key helpers."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# Event types supported in this milestone.
EVENT_TYPES = {
    "run_started",
    "node_started",
    "node_completed",
    "node_failed",
    "run_completed",
    "run_failed",
}


class TraceEvent(BaseModel):
    event_id: str
    run_id: str
    workflow_id: str
    workflow_version_id: str
    node_id: str = ""
    event_type: str
    status: str
    timestamp: datetime
    latency_ms: int = 0
    model_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_name: str = ""
    retry_count: int = 0
    error_message: str = ""
    metadata_json: dict[str, Any] = Field(default_factory=dict)


def run_events_key(run_id: str) -> str:
    """Redis key (a list) where a run's trace events are published.

    A simple Redis list via RPUSH — separate from the job queue
    (`queue:workflow_runs`). Milestone 8 will consume this for live streaming.
    """
    return f"run:{run_id}:events"
