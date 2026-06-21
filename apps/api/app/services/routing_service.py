"""Routing stats: reward computation, stats updates from evals, and queries."""

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.eval import EvalResult
from app.db.models.routing import ModelRoutingStats
from app.db.models.run import WorkflowRun
from app.schemas.routing import RoutingStatResponse

_LATENCY_LIMIT_MS = 5000
_COST_LIMIT_USD = 0.05


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_reward(eval_rows: list[EvalResult], run: WorkflowRun) -> tuple[float, float]:
    """Return (reward, quality) from eval results, with sensible fallbacks."""
    by_type = {r.eval_type: r for r in eval_rows}

    judge = by_type.get("llm_as_judge")
    if judge is not None and judge.quality_score is not None:
        quality = judge.quality_score
    elif eval_rows:
        quality = sum(r.success_score for r in eval_rows) / len(eval_rows)
    else:
        quality = 0.5

    latency_eval = by_type.get("latency")
    if latency_eval is not None and latency_eval.latency_score is not None:
        latency = latency_eval.latency_score
    elif run.total_latency_ms is not None:
        actual = int(run.total_latency_ms)
        latency = 1.0 if actual <= _LATENCY_LIMIT_MS else round(_LATENCY_LIMIT_MS / actual, 4)
    else:
        latency = 0.5

    cost_eval = by_type.get("cost")
    if cost_eval is not None and cost_eval.cost_score is not None:
        cost = cost_eval.cost_score
    elif run.estimated_cost_usd is not None:
        actual_c = float(run.estimated_cost_usd)
        cost = 1.0 if actual_c <= _COST_LIMIT_USD else round(_COST_LIMIT_USD / actual_c, 4)
    else:
        cost = 0.5

    reward = _clamp(0.7 * quality + 0.2 * latency + 0.1 * cost)
    return reward, quality


def _upsert(
    db: Session,
    *,
    run: WorkflowRun,
    route_key: str,
    model_name: str,
    node_id: str,
    reward: float,
    quality: float,
) -> None:
    row = db.scalar(
        select(ModelRoutingStats).where(
            ModelRoutingStats.route_key == route_key,
            ModelRoutingStats.model_name == model_name,
        )
    )
    if row is None:
        row = ModelRoutingStats(
            workflow_id=run.workflow_id,
            workflow_version_id=run.workflow_version_id,
            node_id=node_id or None,
            model_name=model_name,
            route_key=route_key,
            pulls=0,
            total_reward=0.0,
            average_reward=0.0,
            total_latency_ms=0,
            average_latency_ms=0.0,
            total_cost_usd=0.0,
            average_cost_usd=0.0,
            total_quality_score=0.0,
            average_quality_score=0.0,
        )
        db.add(row)

    latency_ms = int(run.total_latency_ms or 0)
    cost = float(run.estimated_cost_usd or 0.0)

    row.pulls += 1
    row.total_reward += reward
    row.average_reward = row.total_reward / row.pulls
    row.total_latency_ms += latency_ms
    row.average_latency_ms = row.total_latency_ms / row.pulls
    row.total_cost_usd += cost
    row.average_cost_usd = row.total_cost_usd / row.pulls
    row.total_quality_score += quality
    row.average_quality_score = row.total_quality_score / row.pulls


def update_routing_stats_from_run(
    db: Session,
    run: WorkflowRun,
    eval_rows: list[EvalResult],
    events: list[dict[str, Any]],
) -> int:
    """Update routing stats for each routing_decision in the run's trace.

    Returns the number of routing decisions counted. Caller ensures this runs
    only once per run (on the first eval) to avoid double-counting.
    """
    decisions = [e for e in events if e.get("event_type") == "routing_decision"]
    if not decisions:
        return 0

    reward, quality = compute_reward(eval_rows, run)
    counted = 0
    for d in decisions:
        meta = d.get("metadata_json") or {}
        route_key = meta.get("route_key") or ""
        selected = meta.get("selected_model") or d.get("model_name") or ""
        node_id = d.get("node_id") or meta.get("node_id") or ""
        if not route_key or not selected:
            continue
        _upsert(
            db,
            run=run,
            route_key=route_key,
            model_name=selected,
            node_id=node_id,
            reward=reward,
            quality=quality,
        )
        counted += 1
    return counted


# --- queries ---


def _to_response(row: ModelRoutingStats) -> RoutingStatResponse:
    return RoutingStatResponse.model_validate(row, from_attributes=True)


def list_stats(
    db: Session,
    *,
    workflow_id: uuid.UUID | None = None,
    workflow_version_id: uuid.UUID | None = None,
    node_id: str | None = None,
    route_key: str | None = None,
) -> list[RoutingStatResponse]:
    stmt = select(ModelRoutingStats)
    if workflow_id is not None:
        stmt = stmt.where(ModelRoutingStats.workflow_id == workflow_id)
    if workflow_version_id is not None:
        stmt = stmt.where(ModelRoutingStats.workflow_version_id == workflow_version_id)
    if node_id is not None:
        stmt = stmt.where(ModelRoutingStats.node_id == node_id)
    if route_key is not None:
        stmt = stmt.where(ModelRoutingStats.route_key == route_key)
    stmt = stmt.order_by(
        ModelRoutingStats.route_key, ModelRoutingStats.average_reward.desc()
    )
    return [_to_response(r) for r in db.scalars(stmt)]


def get_stats_for_route(db: Session, route_key: str) -> list[RoutingStatResponse]:
    return list_stats(db, route_key=route_key)


def reset_stats(db: Session) -> int:
    result = db.execute(delete(ModelRoutingStats))
    db.commit()
    return result.rowcount or 0
