"""Trace retrieval: verify the run exists, then read events from the TraceStore."""

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.run_repository import RunRepository
from app.db.trace_store import TraceStore
from app.schemas.trace import TraceEventResponse
from app.services.exceptions import RunNotFoundError


def _load_metadata(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def _row_to_response(row: tuple[Any, ...]) -> TraceEventResponse:
    return TraceEventResponse(
        event_id=str(row[0]),
        run_id=str(row[1]),
        workflow_id=str(row[2]),
        workflow_version_id=str(row[3]),
        node_id=row[4] or "",
        event_type=row[5],
        status=row[6],
        timestamp=row[7],
        latency_ms=int(row[8]),
        model_name=row[9] or "",
        input_tokens=int(row[10]),
        output_tokens=int(row[11]),
        estimated_cost_usd=float(row[12]),
        tool_name=row[13] or "",
        retry_count=int(row[14]),
        error_message=row[15] or "",
        metadata_json=_load_metadata(row[16]),
    )


def get_run_trace(
    db: Session, store: TraceStore, run_id: uuid.UUID
) -> list[TraceEventResponse]:
    run = RunRepository(db).get(run_id)
    if run is None:
        raise RunNotFoundError(str(run_id))

    # Idempotent — ensures reads don't 500 before any trace has been written.
    store.ensure_ready()
    rows = store.get_events_by_run_id(run_id)
    return [_row_to_response(r) for r in rows]
