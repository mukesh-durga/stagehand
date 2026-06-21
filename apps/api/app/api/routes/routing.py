"""Model routing stats endpoints (UCB dashboard)."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.schemas.routing import RoutingStatResponse
from app.services import routing_service

router = APIRouter(tags=["routing"])


@router.get("/routing/stats", response_model=list[RoutingStatResponse])
def list_routing_stats(
    workflow_id: uuid.UUID | None = Query(default=None),
    workflow_version_id: uuid.UUID | None = Query(default=None),
    node_id: str | None = Query(default=None),
    route_key: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RoutingStatResponse]:
    return routing_service.list_stats(
        db,
        workflow_id=workflow_id,
        workflow_version_id=workflow_version_id,
        node_id=node_id,
        route_key=route_key,
    )


@router.get("/routing/stats/{route_key}", response_model=list[RoutingStatResponse])
def get_routing_stats_for_route(
    route_key: str, db: Session = Depends(get_db)
) -> list[RoutingStatResponse]:
    return routing_service.get_stats_for_route(db, route_key)


@router.post("/routing/stats/reset")
def reset_routing_stats(db: Session = Depends(get_db)) -> dict[str, int]:
    """Development helper: clear all routing stats."""
    deleted = routing_service.reset_stats(db)
    return {"deleted": deleted}
