"""Usage tracking and billing endpoints."""

import uuid

from clickhouse_connect.driver.client import Client
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.clickhouse import get_clickhouse
from app.db.postgres import get_db
from app.schemas.usage import (
    BillingStatusResponse,
    CheckoutSessionResponse,
    UsageEventResponse,
    UsageSummaryResponse,
)
from app.services import billing_service, usage_service

router = APIRouter(tags=["usage"])


@router.get("/usage/events", response_model=list[UsageEventResponse])
def list_usage_events(
    run_id: uuid.UUID | None = Query(default=None),
    workflow_id: uuid.UUID | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> list[UsageEventResponse]:
    return usage_service.list_usage_events(
        db, run_id=run_id, workflow_id=workflow_id, event_type=event_type, limit=limit
    )


@router.get("/usage/summary", response_model=UsageSummaryResponse)
def get_usage_summary(db: Session = Depends(get_db)) -> UsageSummaryResponse:
    return usage_service.get_usage_summary(db)


@router.post("/usage/backfill")
def backfill_usage(
    db: Session = Depends(get_db),
    clickhouse_client: Client = Depends(get_clickhouse),
) -> dict[str, int]:
    inserted = usage_service.backfill(db, clickhouse_client)
    return {"inserted": inserted}


@router.get("/billing/status", response_model=BillingStatusResponse)
def billing_status() -> BillingStatusResponse:
    return billing_service.get_billing_status()


@router.post("/billing/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session() -> CheckoutSessionResponse:
    return billing_service.create_checkout_session()
