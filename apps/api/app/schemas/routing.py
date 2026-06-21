"""Schemas for model routing stats."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class RoutingStatResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID | None
    workflow_version_id: uuid.UUID | None
    node_id: str | None
    model_name: str
    route_key: str
    pulls: int
    total_reward: float
    average_reward: float
    total_latency_ms: int
    average_latency_ms: float
    total_cost_usd: float
    average_cost_usd: float
    total_quality_score: float
    average_quality_score: float
    created_at: datetime
    updated_at: datetime
