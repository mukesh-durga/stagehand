"""Eval harness: score a completed/failed run with multiple evaluators.

Deterministic MVP evaluators (no API keys required). The llm_as_judge evaluator
uses a deterministic mock judge structured so a real judge can replace it later.
"""

import json
import uuid
from collections.abc import Callable
from typing import Any

from clickhouse_connect.driver.client import Client
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.clickhouse import ensure_trace_table, query_run_trace_events
from app.db.models.eval import EvalResult
from app.db.models.run import WorkflowRun
from app.db.repositories.run_repository import RunRepository
from app.schemas.eval import DEFAULT_EVAL_TYPES, EVAL_TYPES, EvalRequest, EvalResultResponse
from app.services.diff_service import _rows_to_dicts
from app.services.exceptions import (
    RunNotEvaluatableError,
    RunNotFoundError,
    UnknownEvalTypeError,
)

DEFAULT_MAX_LATENCY_MS = 5000
DEFAULT_MAX_COST_USD = 0.05


def _to_response(row: EvalResult) -> EvalResultResponse:
    return EvalResultResponse(
        id=row.id,
        run_id=row.run_id,
        workflow_id=row.workflow_id,
        workflow_version_id=row.workflow_version_id,
        eval_type=row.eval_type,
        success_score=row.success_score,
        tool_correctness_score=row.tool_correctness_score,
        format_score=row.format_score,
        quality_score=row.quality_score,
        cost_score=row.cost_score,
        latency_score=row.latency_score,
        passed=row.passed,
        feedback=row.feedback,
        metadata_json=row.metadata_json or {},
        created_at=row.created_at,
    )


# --- evaluators: each returns the EvalResult fields to persist ---


def _exact_match(run: WorkflowRun, events: list[dict], req: EvalRequest) -> dict[str, Any]:
    actual = json.dumps(run.output_json if run.output_json is not None else {}, sort_keys=True)
    expected = json.dumps(
        req.expected_output if req.expected_output is not None else {}, sort_keys=True
    )
    score = 1.0 if actual == expected else 0.0
    return {
        "success_score": score,
        "format_score": score,
        "passed": score == 1.0,
        "feedback": "Output matches expected." if score else "Output differs from expected.",
        "metadata_json": {"expected": req.expected_output, "actual": run.output_json},
    }


def _json_schema(run: WorkflowRun, events: list[dict], req: EvalRequest) -> dict[str, Any]:
    import jsonschema

    schema = req.expected_schema or {}
    actual = run.output_json or {}
    try:
        jsonschema.validate(actual, schema)
        score, feedback = 1.0, "Output matches schema."
    except jsonschema.ValidationError as exc:
        score, feedback = 0.0, f"Schema validation failed: {exc.message}"
    except Exception as exc:  # noqa: BLE001 - invalid schema etc.
        score, feedback = 0.0, f"Schema error: {exc}"
    return {
        "success_score": score,
        "format_score": score,
        "passed": score == 1.0,
        "feedback": feedback,
        "metadata_json": {"schema": schema},
    }


def _tool_usage(run: WorkflowRun, events: list[dict], req: EvalRequest) -> dict[str, Any]:
    expected = req.expected_tools or []
    used = {
        e.get("tool_name")
        for e in events
        if e.get("event_type") in ("tool_called", "tool_completed") and e.get("tool_name")
    }
    if not expected:
        score, feedback = 1.0, "No tools required."
    else:
        matched = [t for t in expected if t in used]
        score = len(matched) / len(expected)
        feedback = f"Used {sorted(used)}; expected {expected}."
    return {
        "success_score": score,
        "tool_correctness_score": score,
        "passed": score == 1.0,
        "feedback": feedback,
        "metadata_json": {"expected_tools": expected, "tools_used": sorted(used)},
    }


def _latency(run: WorkflowRun, events: list[dict], req: EvalRequest) -> dict[str, Any]:
    limit = req.max_latency_ms if req.max_latency_ms is not None else DEFAULT_MAX_LATENCY_MS
    actual = int(run.total_latency_ms or 0)
    if actual <= limit:
        score = 1.0
    elif actual > 0:
        score = round(limit / actual, 4)
    else:
        score = 1.0
    return {
        "success_score": score,
        "latency_score": score,
        "passed": actual <= limit,
        "feedback": f"{actual} ms vs limit {limit} ms",
        "metadata_json": {"actual_ms": actual, "limit_ms": limit},
    }


def _cost(run: WorkflowRun, events: list[dict], req: EvalRequest) -> dict[str, Any]:
    limit = req.max_cost_usd if req.max_cost_usd is not None else DEFAULT_MAX_COST_USD
    actual = float(run.estimated_cost_usd or 0.0)
    if actual <= limit:
        score = 1.0
    elif actual > 0:
        score = round(limit / actual, 4)
    else:
        score = 1.0
    return {
        "success_score": score,
        "cost_score": score,
        "passed": actual <= limit,
        "feedback": f"${actual} vs limit ${limit}",
        "metadata_json": {"actual_usd": actual, "limit_usd": limit},
    }


def _llm_as_judge(run: WorkflowRun, events: list[dict], req: EvalRequest) -> dict[str, Any]:
    # Deterministic mock judge — pluggable for a real LLM judge later.
    has_output = bool(run.output_json)
    completed = run.status == "completed"
    quality = 0.85 if (has_output and completed) else 0.4
    passed = quality >= 0.6
    feedback = (
        "Mock judge: output is coherent and addresses the task."
        if passed
        else "Mock judge: output missing or run did not complete successfully."
    )
    return {
        "success_score": quality,
        "quality_score": quality,
        "passed": passed,
        "feedback": feedback,
        "metadata_json": {"judge": "mock", "judge_prompt": (req.judge_prompt or "")[:200]},
    }


EVALUATORS: dict[str, Callable[[WorkflowRun, list[dict], EvalRequest], dict[str, Any]]] = {
    "exact_match": _exact_match,
    "json_schema": _json_schema,
    "tool_usage": _tool_usage,
    "latency": _latency,
    "cost": _cost,
    "llm_as_judge": _llm_as_judge,
}


def run_eval(
    db: Session,
    clickhouse_client: Client,
    run_id: uuid.UUID,
    request: EvalRequest,
) -> list[EvalResultResponse]:
    run = RunRepository(db).get(run_id)
    if run is None:
        raise RunNotFoundError(str(run_id))
    if run.status not in ("completed", "failed"):
        raise RunNotEvaluatableError(run.status)

    eval_types = request.eval_types or list(DEFAULT_EVAL_TYPES)
    unknown = [t for t in eval_types if t not in EVAL_TYPES]
    if unknown:
        raise UnknownEvalTypeError(", ".join(unknown))

    # Trace events are only needed for tool_usage.
    events: list[dict] = []
    if "tool_usage" in eval_types:
        ensure_trace_table(clickhouse_client)
        events = _rows_to_dicts(query_run_trace_events(clickhouse_client, str(run_id)))

    rows: list[EvalResult] = []
    for eval_type in eval_types:
        fields = EVALUATORS[eval_type](run, events, request)
        row = EvalResult(
            run_id=run.id,
            workflow_id=run.workflow_id,
            workflow_version_id=run.workflow_version_id,
            eval_type=eval_type,
            **fields,
        )
        db.add(row)
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)
    return [_to_response(r) for r in rows]


def list_evals(db: Session, run_id: uuid.UUID) -> list[EvalResultResponse]:
    stmt = (
        select(EvalResult)
        .where(EvalResult.run_id == run_id)
        .order_by(EvalResult.created_at.desc())
    )
    return [_to_response(r) for r in db.scalars(stmt)]


def get_eval(db: Session, eval_id: uuid.UUID) -> EvalResultResponse | None:
    row = db.get(EvalResult, eval_id)
    return _to_response(row) if row is not None else None
