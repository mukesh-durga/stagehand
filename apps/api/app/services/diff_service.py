"""Compare two runs node-by-node and event-by-event."""

import json
import uuid
from collections import Counter
from typing import Any

from clickhouse_connect.driver.client import Client
from sqlalchemy.orm import Session

from app.db.clickhouse import TRACE_COLUMNS, ensure_trace_table, query_run_trace_events
from app.db.repositories.run_repository import RunRepository
from app.schemas.diff import (
    EventDiff,
    NodeDiff,
    OutputDiff,
    RunDiffResponse,
    RunDiffSummary,
)
from app.services.exceptions import RunNotFoundError
from app.services.run_service import _to_response


def _rows_to_dicts(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        event = dict(zip(TRACE_COLUMNS, row, strict=False))
        meta = event.get("metadata_json")
        if isinstance(meta, str):
            try:
                event["metadata_json"] = json.loads(meta) if meta else {}
            except (TypeError, ValueError):
                event["metadata_json"] = {}
        out.append(event)
    return out


def _empty_node() -> dict[str, Any]:
    return {
        "status": "",
        "model": "",
        "tool": "",
        "latency": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost": 0.0,
        "retry_count": 0,
        "fallback_used": False,
        "error": "",
        "output_summary": "",
    }


def _aggregate(events: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    models: set[str] = set()
    tools: set[str] = set()
    retries = 0
    fallback = False

    for e in events:
        node_id = e.get("node_id") or ""
        et = e.get("event_type")
        node = nodes.setdefault(node_id, _empty_node()) if node_id else None

        if et == "model_completed":
            if e.get("model_name"):
                models.add(e["model_name"])
            if node is not None:
                node["model"] = e.get("model_name", "")
                node["input_tokens"] = int(e.get("input_tokens") or 0)
                node["output_tokens"] = int(e.get("output_tokens") or 0)
                node["cost"] = float(e.get("estimated_cost_usd") or 0.0)
        elif et in ("tool_called", "tool_completed", "tool_failed"):
            if e.get("tool_name"):
                tools.add(e["tool_name"])
                if node is not None:
                    node["tool"] = e["tool_name"]
            if et == "tool_failed" and node is not None:
                node["error"] = e.get("error_message", "")
        elif et == "node_completed":
            if node is not None:
                node["status"] = "success"
                node["latency"] = int(e.get("latency_ms") or 0)
                node["output_summary"] = str(e.get("metadata_json", {}).get("output_type", ""))
        elif et == "node_failed":
            if node is not None:
                node["status"] = "failed"
                node["latency"] = int(e.get("latency_ms") or 0)
                node["error"] = e.get("error_message", "")
        elif et == "retry_scheduled":
            retries += 1
            if node is not None:
                node["retry_count"] += 1
        elif et == "fallback_used":
            fallback = True
            if node is not None:
                node["fallback_used"] = True

    return {"nodes": nodes, "models": models, "tools": tools, "retries": retries, "fallback": fallback}


def _node_diff(node_id: str, a: dict[str, Any], b: dict[str, Any]) -> NodeDiff:
    return NodeDiff(
        node_id=node_id,
        status_a=a["status"],
        status_b=b["status"],
        status_changed=a["status"] != b["status"],
        model_a=a["model"],
        model_b=b["model"],
        model_changed=a["model"] != b["model"],
        tool_a=a["tool"],
        tool_b=b["tool"],
        tool_changed=a["tool"] != b["tool"],
        latency_a_ms=a["latency"],
        latency_b_ms=b["latency"],
        latency_delta_ms=b["latency"] - a["latency"],
        input_tokens_a=a["input_tokens"],
        input_tokens_b=b["input_tokens"],
        output_tokens_a=a["output_tokens"],
        output_tokens_b=b["output_tokens"],
        cost_a=a["cost"],
        cost_b=b["cost"],
        cost_delta=round(b["cost"] - a["cost"], 8),
        retry_count_a=a["retry_count"],
        retry_count_b=b["retry_count"],
        fallback_used_a=a["fallback_used"],
        fallback_used_b=b["fallback_used"],
        error_a=a["error"],
        error_b=b["error"],
        output_summary_a=a["output_summary"],
        output_summary_b=b["output_summary"],
    )


def _event_diffs(
    events_a: list[dict[str, Any]], events_b: list[dict[str, Any]]
) -> list[EventDiff]:
    def key_counts(events: list[dict[str, Any]]) -> Counter:
        return Counter((e.get("event_type", ""), e.get("node_id") or "") for e in events)

    ca, cb = key_counts(events_a), key_counts(events_b)
    diffs: list[EventDiff] = []
    for et, node_id in sorted(set(ca) | set(cb)):
        count_a, count_b = ca.get((et, node_id), 0), cb.get((et, node_id), 0)
        diffs.append(
            EventDiff(
                event_type=et,
                node_id=node_id,
                count_a=count_a,
                count_b=count_b,
                changed=count_a != count_b,
            )
        )
    return diffs


def _summarize_json(data: Any, limit: int = 400) -> str:
    text = json.dumps(data or {}, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "…"


def diff_runs(
    db: Session,
    clickhouse_client: Client,
    run_id: uuid.UUID,
    other_run_id: uuid.UUID,
) -> RunDiffResponse:
    repo = RunRepository(db)
    run_a = repo.get(run_id)
    run_b = repo.get(other_run_id)
    if run_a is None:
        raise RunNotFoundError(str(run_id))
    if run_b is None:
        raise RunNotFoundError(str(other_run_id))

    ensure_trace_table(clickhouse_client)
    events_a = _rows_to_dicts(query_run_trace_events(clickhouse_client, str(run_id)))
    events_b = _rows_to_dicts(query_run_trace_events(clickhouse_client, str(other_run_id)))

    agg_a = _aggregate(events_a)
    agg_b = _aggregate(events_b)

    node_ids = sorted(set(agg_a["nodes"]) | set(agg_b["nodes"]))
    node_diffs = [
        _node_diff(
            nid,
            agg_a["nodes"].get(nid, _empty_node()),
            agg_b["nodes"].get(nid, _empty_node()),
        )
        for nid in node_ids
    ]

    out_a = _summarize_json(run_a.output_json)
    out_b = _summarize_json(run_b.output_json)
    output_diff = OutputDiff(
        changed=json.dumps(run_a.output_json or {}, sort_keys=True)
        != json.dumps(run_b.output_json or {}, sort_keys=True),
        output_a_summary=out_a,
        output_b_summary=out_b,
    )

    def m(value: Any) -> int:
        return int(value or 0)

    summary = RunDiffSummary(
        status_changed=run_a.status != run_b.status,
        workflow_version_changed=run_a.workflow_version_id != run_b.workflow_version_id,
        latency_delta_ms=m(run_b.total_latency_ms) - m(run_a.total_latency_ms),
        input_tokens_delta=m(run_b.total_input_tokens) - m(run_a.total_input_tokens),
        output_tokens_delta=m(run_b.total_output_tokens) - m(run_a.total_output_tokens),
        cost_delta=round(
            float(run_b.estimated_cost_usd or 0) - float(run_a.estimated_cost_usd or 0), 8
        ),
        error_changed=(run_a.error_message or "") != (run_b.error_message or ""),
        model_changed=agg_a["models"] != agg_b["models"],
        tool_changed=agg_a["tools"] != agg_b["tools"],
        retry_count_delta=agg_b["retries"] - agg_a["retries"],
        fallback_changed=agg_a["fallback"] != agg_b["fallback"],
    )

    return RunDiffResponse(
        run_a=_to_response(run_a),
        run_b=_to_response(run_b),
        summary=summary,
        node_diffs=node_diffs,
        event_diffs=_event_diffs(events_a, events_b),
        output_diff=output_diff,
    )
