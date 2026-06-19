"""Pydantic schema for trace events (API read path)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TraceEventResponse(BaseModel):
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
