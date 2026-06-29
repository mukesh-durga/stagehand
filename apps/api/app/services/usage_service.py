"""Usage tracking: record per-run usage events, summarize, and backfill."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.run import WorkflowRun
from app.db.models.usage import UsageEvent
from app.db.trace_store import TraceStore
from app.schemas.usage import UsageEventResponse, UsageSummaryResponse
from app.services.diff_service import _rows_to_dicts


def _build_usage_events(
    run: WorkflowRun, trace_events: list[dict[str, Any]]
) -> list[UsageEvent]:
    """Build (not persist) usage events for a run from its trace events."""
    events: list[UsageEvent] = []
    model_cost_total = 0.0

    for e in trace_events:
        if e.get("event_type") == "model_completed":
            in_tok = int(e.get("input_tokens") or 0)
            out_tok = int(e.get("output_tokens") or 0)
            cost = float(e.get("estimated_cost_usd") or 0.0)
            model_cost_total += cost
            events.append(
                UsageEvent(
                    run_id=run.id,
                    workflow_id=run.workflow_id,
                    workflow_version_id=run.workflow_version_id,
                    event_type="model_usage",
                    model_name=e.get("model_name") or None,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    total_tokens=in_tok + out_tok,
                    estimated_cost_usd=cost,
                    quantity=1,
                )
            )
        elif e.get("event_type") == "tool_completed":
            events.append(
                UsageEvent(
                    run_id=run.id,
                    workflow_id=run.workflow_id,
                    workflow_version_id=run.workflow_version_id,
                    event_type="tool_usage",
                    tool_name=e.get("tool_name") or None,
                    quantity=1,
                    estimated_cost_usd=0.0,
                )
            )

    run_cost = (
        float(run.estimated_cost_usd)
        if run.estimated_cost_usd is not None
        else model_cost_total
    )
    events.append(
        UsageEvent(
            run_id=run.id,
            workflow_id=run.workflow_id,
            workflow_version_id=run.workflow_version_id,
            event_type="run_completed",
            input_tokens=int(run.total_input_tokens or 0),
            output_tokens=int(run.total_output_tokens or 0),
            total_tokens=int((run.total_input_tokens or 0) + (run.total_output_tokens or 0)),
            estimated_cost_usd=run_cost,
            quantity=1,
        )
    )
    return events


def record_run_usage(
    db: Session, run: WorkflowRun, trace_events: list[dict[str, Any]]
) -> int:
    """Idempotently record usage events for a run. Returns rows inserted."""
    existing = db.scalar(
        select(func.count()).select_from(UsageEvent).where(UsageEvent.run_id == run.id)
    )
    if existing:
        return 0
    events = _build_usage_events(run, trace_events)
    db.add_all(events)
    db.commit()
    return len(events)


def backfill(db: Session, store: TraceStore) -> int:
    """Record usage for completed/failed runs that have none yet."""
    store.ensure_ready()
    runs = db.scalars(
        select(WorkflowRun).where(WorkflowRun.status.in_(("completed", "failed")))
    ).all()
    total = 0
    for run in runs:
        existing = db.scalar(
            select(func.count()).select_from(UsageEvent).where(UsageEvent.run_id == run.id)
        )
        if existing:
            continue
        trace_events = _rows_to_dicts(store.get_events_by_run_id(run.id))
        total += record_run_usage(db, run, trace_events)
    return total


def _to_response(row: UsageEvent) -> UsageEventResponse:
    return UsageEventResponse.model_validate(row, from_attributes=True)


def list_usage_events(
    db: Session,
    *,
    run_id: uuid.UUID | None = None,
    workflow_id: uuid.UUID | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[UsageEventResponse]:
    stmt = select(UsageEvent)
    if run_id is not None:
        stmt = stmt.where(UsageEvent.run_id == run_id)
    if workflow_id is not None:
        stmt = stmt.where(UsageEvent.workflow_id == workflow_id)
    if event_type is not None:
        stmt = stmt.where(UsageEvent.event_type == event_type)
    stmt = stmt.order_by(UsageEvent.created_at.desc()).limit(limit)
    return [_to_response(r) for r in db.scalars(stmt)]


def get_usage_summary(db: Session) -> UsageSummaryResponse:
    def count(event_type: str) -> int:
        return db.scalar(
            select(func.count())
            .select_from(UsageEvent)
            .where(UsageEvent.event_type == event_type)
        ) or 0

    total_runs = count("run_completed")
    total_model_calls = count("model_usage")
    total_tool_calls = count("tool_usage")

    # Tokens are summed over model_usage events.
    in_tok, out_tok, tok = db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.input_tokens), 0),
            func.coalesce(func.sum(UsageEvent.output_tokens), 0),
            func.coalesce(func.sum(UsageEvent.total_tokens), 0),
        ).where(UsageEvent.event_type == "model_usage")
    ).one()

    # Total cost summed over run_completed events (avoids double-counting models).
    total_cost = db.scalar(
        select(func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0.0)).where(
            UsageEvent.event_type == "run_completed"
        )
    ) or 0.0

    cost_by_model = {
        (m or "unknown"): round(float(c), 6)
        for m, c in db.execute(
            select(UsageEvent.model_name, func.sum(UsageEvent.estimated_cost_usd))
            .where(UsageEvent.event_type == "model_usage")
            .group_by(UsageEvent.model_name)
        ).all()
    }

    cost_by_workflow = {
        str(w): round(float(c), 6)
        for w, c in db.execute(
            select(UsageEvent.workflow_id, func.sum(UsageEvent.estimated_cost_usd))
            .where(UsageEvent.event_type == "run_completed")
            .group_by(UsageEvent.workflow_id)
        ).all()
        if w is not None
    }

    usage_by_day = {
        d.strftime("%Y-%m-%d"): int(n)
        for d, n in db.execute(
            select(func.date(UsageEvent.created_at), func.count())
            .where(UsageEvent.event_type == "run_completed")
            .group_by(func.date(UsageEvent.created_at))
            .order_by(func.date(UsageEvent.created_at))
        ).all()
    }

    return UsageSummaryResponse(
        total_runs=total_runs,
        total_model_calls=total_model_calls,
        total_tool_calls=total_tool_calls,
        total_input_tokens=int(in_tok),
        total_output_tokens=int(out_tok),
        total_tokens=int(tok),
        total_estimated_cost_usd=round(float(total_cost), 6),
        cost_by_model=cost_by_model,
        cost_by_workflow=cost_by_workflow,
        usage_by_day=usage_by_day,
    )
