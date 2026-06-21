"""Record usage events for a completed run (idempotent, best-effort).

Uses the in-memory trace events the orchestrator already emitted, so no extra
ClickHouse query is needed. Mirrors the API's usage_service event shapes.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from worker.models import UsageEvent, WorkflowRun

logger = logging.getLogger(__name__)


def _build_events(run: WorkflowRun, trace_events: list[Any]) -> list[UsageEvent]:
    events: list[UsageEvent] = []
    model_cost_total = 0.0

    for e in trace_events:
        if e.event_type == "model_completed":
            in_tok = int(e.input_tokens or 0)
            out_tok = int(e.output_tokens or 0)
            cost = float(e.estimated_cost_usd or 0.0)
            model_cost_total += cost
            events.append(
                UsageEvent(
                    run_id=run.id,
                    workflow_id=run.workflow_id,
                    workflow_version_id=run.workflow_version_id,
                    event_type="model_usage",
                    model_name=e.model_name or None,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    total_tokens=in_tok + out_tok,
                    estimated_cost_usd=cost,
                    quantity=1,
                    metadata_json={},
                )
            )
        elif e.event_type == "tool_completed":
            events.append(
                UsageEvent(
                    run_id=run.id,
                    workflow_id=run.workflow_id,
                    workflow_version_id=run.workflow_version_id,
                    event_type="tool_usage",
                    tool_name=e.tool_name or None,
                    quantity=1,
                    estimated_cost_usd=0.0,
                    metadata_json={},
                )
            )

    run_cost = (
        float(run.estimated_cost_usd)
        if run.estimated_cost_usd is not None
        else model_cost_total
    )
    in_total = int(run.total_input_tokens or 0)
    out_total = int(run.total_output_tokens or 0)
    events.append(
        UsageEvent(
            run_id=run.id,
            workflow_id=run.workflow_id,
            workflow_version_id=run.workflow_version_id,
            event_type="run_completed",
            input_tokens=in_total,
            output_tokens=out_total,
            total_tokens=in_total + out_total,
            estimated_cost_usd=run_cost,
            quantity=1,
            metadata_json={},
        )
    )
    return events


def record_run_usage(db: Session, run: WorkflowRun, trace_events: list[Any]) -> int:
    """Idempotently record usage events for a run. Best-effort, never raises."""
    try:
        existing = db.scalar(
            select(func.count()).select_from(UsageEvent).where(UsageEvent.run_id == run.id)
        )
        if existing:
            return 0
        events = _build_events(run, trace_events)
        db.add_all(events)
        db.commit()
        return len(events)
    except Exception:  # noqa: BLE001 - usage recording must never break a run
        logger.warning("failed to record usage for run %s", run.id, exc_info=True)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return 0
