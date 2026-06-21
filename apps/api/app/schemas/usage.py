"""Schemas for usage tracking and billing status."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class UsageEventResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID | None
    workflow_id: uuid.UUID | None
    workflow_version_id: uuid.UUID | None
    event_type: str
    model_name: str | None
    tool_name: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    quantity: int
    metadata_json: dict[str, Any]
    created_at: datetime


class UsageSummaryResponse(BaseModel):
    total_runs: int
    total_model_calls: int
    total_tool_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_estimated_cost_usd: float
    cost_by_model: dict[str, float]
    cost_by_workflow: dict[str, float]
    usage_by_day: dict[str, int]


class BillingStatusResponse(BaseModel):
    mode: str
    stripe_configured: bool
    customer_id: str | None = None
    checkout_url: str | None = None
    status: str


class CheckoutSessionResponse(BaseModel):
    mode: str
    checkout_url: str
    session_id: str | None = None
