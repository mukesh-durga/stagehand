"""Hosted-demo workflow executor.

A lightweight, mock-only execution path that runs *inside the API* as a background
task when there is no separate worker (free-tier hosted demo). It mirrors the
worker engine's trace-event shape closely enough that the run-detail timeline,
diff, eval, usage, and routing-stats features all work — but uses only
deterministic mock providers and tiny in-memory work, so it is safe and cheap on
free hosting.

Local full-stack mode is unaffected: when WORKER_ENABLED=true the run is enqueued
to Redis and executed by the real worker engine instead (see run_service).
"""

from __future__ import annotations

import ast
import logging
import operator
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models.run import WorkflowRun
from app.db.models.workflow import WorkflowVersion
from app.db.postgres import SessionLocal
from app.db.redis import run_events_key
from app.db.trace_store import TraceRecord, TraceStore, make_trace_store
from app.services import usage_service

logger = logging.getLogger(__name__)

# Mock per-token cost (USD) so cost analytics show non-trivial, deterministic values.
_COST_PER_OUTPUT_TOKEN = 0.000002


# --- tiny safe arithmetic (calculator tool) ---

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(
        node.value, bool
    ):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        if isinstance(node.op, ast.Pow) and _safe_eval(node.right) > 100:
            raise ValueError("Exponent too large.")
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression.")


def _calculator(tool_input: dict[str, Any]) -> dict[str, Any]:
    expression = str(tool_input.get("expression") or "").strip() or "1 + 1"
    return {"expression": expression, "result": _safe_eval(ast.parse(expression, mode="eval"))}


def _mock_search(tool_input: dict[str, Any]) -> dict[str, Any]:
    query = str(tool_input.get("query") or "").strip() or "stagehand"
    return {
        "query": query,
        "results": [
            {"title": f"Result {i + 1} for {query}", "snippet": f"Snippet {i + 1} about {query}."}
            for i in range(3)
        ],
    }


def _run_tool(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "calculator":
        return _calculator(tool_input)
    if tool_name == "mock_search":
        return _mock_search(tool_input)
    # Unknown/echo tools degrade gracefully rather than failing the demo run.
    return {"tool": tool_name, "echo": tool_input}


# --- trace emitter (Redis live publish + buffered store insert) ---


class DemoTraceEmitter:
    """Builds trace events, publishes to Redis live, and buffers for storage."""

    def __init__(self, run: WorkflowRun, redis_client: Any | None) -> None:
        self.run_id = str(run.id)
        self.workflow_id = str(run.workflow_id)
        self.workflow_version_id = str(run.workflow_version_id)
        self.redis_client = redis_client
        self.events: list[TraceRecord] = []

    def emit(self, event_type: str, status: str, **kwargs: Any) -> TraceRecord:
        event = TraceRecord(
            event_id=str(uuid.uuid4()),
            run_id=self.run_id,
            workflow_id=self.workflow_id,
            workflow_version_id=self.workflow_version_id,
            event_type=event_type,
            status=status,
            timestamp=datetime.now(timezone.utc),
            node_id=kwargs.get("node_id", ""),
            latency_ms=int(kwargs.get("latency_ms", 0)),
            model_name=kwargs.get("model_name", ""),
            input_tokens=int(kwargs.get("input_tokens", 0)),
            output_tokens=int(kwargs.get("output_tokens", 0)),
            estimated_cost_usd=float(kwargs.get("estimated_cost_usd", 0.0)),
            tool_name=kwargs.get("tool_name", ""),
            retry_count=int(kwargs.get("retry_count", 0)),
            error_message=kwargs.get("error_message", ""),
            metadata_json=kwargs.get("metadata") or {},
        )
        self.events.append(event)
        self._publish(event)
        return event

    def _publish(self, event: TraceRecord) -> None:
        if self.redis_client is None:
            return
        payload = {
            "event_id": event.event_id,
            "run_id": event.run_id,
            "workflow_id": event.workflow_id,
            "workflow_version_id": event.workflow_version_id,
            "node_id": event.node_id,
            "event_type": event.event_type,
            "status": event.status,
            "timestamp": event.timestamp.isoformat(),
            "latency_ms": event.latency_ms,
            "model_name": event.model_name,
            "input_tokens": event.input_tokens,
            "output_tokens": event.output_tokens,
            "estimated_cost_usd": event.estimated_cost_usd,
            "tool_name": event.tool_name,
            "retry_count": event.retry_count,
            "error_message": event.error_message,
            "metadata_json": event.metadata_json,
        }
        try:
            import json

            self.redis_client.rpush(run_events_key(self.run_id), json.dumps(payload))
        except Exception:  # noqa: BLE001 - live publish is best-effort
            logger.debug("demo trace publish to Redis failed", exc_info=True)

    def as_usage_dicts(self) -> list[dict[str, Any]]:
        return [
            {
                "event_type": e.event_type,
                "model_name": e.model_name,
                "input_tokens": e.input_tokens,
                "output_tokens": e.output_tokens,
                "estimated_cost_usd": e.estimated_cost_usd,
                "tool_name": e.tool_name,
            }
            for e in self.events
        ]


# --- graph helpers ---


def _topological_order(nodes: list[dict], edges: list[dict]) -> list[str]:
    ids = [n["id"] for n in nodes]
    indegree = {i: 0 for i in ids}
    adjacency: dict[str, list[str]] = {i: [] for i in ids}
    for edge in edges:
        s, t = edge.get("source"), edge.get("target")
        if s in adjacency and t in indegree:
            adjacency[s].append(t)
            indegree[t] += 1
    queue = deque([i for i in ids if indegree[i] == 0])
    order: list[str] = []
    while queue:
        cur = queue.popleft()
        order.append(cur)
        for nb in adjacency[cur]:
            indegree[nb] -= 1
            if indegree[nb] == 0:
                queue.append(nb)
    if len(order) != len(ids):
        raise ValueError("Graph contains a cycle.")
    return order


def _predecessors(edges: list[dict]) -> dict[str, list[str]]:
    preds: dict[str, list[str]] = {}
    for edge in edges:
        preds.setdefault(edge.get("target"), []).append(edge.get("source"))
    return preds


def _resolve_model(policy: str, settings: Any) -> str:
    if policy == "strong":
        return settings.strong_model_name or "mock-strong"
    return settings.cheap_model_name or "mock-cheap"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _execute_agent(
    node: dict, node_input: Any, emitter: DemoTraceEmitter, settings: Any
) -> dict[str, Any]:
    config = node.get("config") or node.get("data") or {}
    node_id = node["id"]
    policy = config.get("modelPolicy") or config.get("model_policy") or "adaptive"
    prompt = config.get("prompt") or "You are a helpful agent."

    if policy == "adaptive":
        cheap = _resolve_model("cheap", settings)
        strong = _resolve_model("strong", settings)
        # Deterministic selection (cheap) — keeps the demo cheap and reproducible.
        model_name = cheap
        route_key = f"{emitter.workflow_id}:{emitter.workflow_version_id}:{node_id}"
        emitter.emit(
            "routing_decision",
            "running",
            node_id=node_id,
            model_name=model_name,
            metadata={
                "route_key": route_key,
                "policy": policy,
                "selected_model": model_name,
                "candidate_models": [cheap, strong],
                "reason": "hosted_demo deterministic selection",
            },
        )
    else:
        model_name = _resolve_model(policy, settings)

    emitter.emit("model_called", "running", node_id=node_id, model_name=model_name,
                 metadata={"model_policy": policy, "prompt_summary": prompt[:200]})

    user_text = node_input if isinstance(node_input, str) else str(node_input)
    text = f"Mock model response for: {user_text[:80]}" if user_text else "Mock model response"
    input_tokens = _estimate_tokens(prompt + user_text)
    output_tokens = len(text.split())
    cost = round(output_tokens * _COST_PER_OUTPUT_TOKEN, 8)

    emitter.emit(
        "model_completed",
        "success",
        node_id=node_id,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
        latency_ms=1,
        metadata={"output_summary": text[:200]},
    )
    return {"type": "agent_output", "node_id": node_id, "model": model_name, "text": text}


def _execute_tool(node: dict, node_input: Any, emitter: DemoTraceEmitter) -> dict[str, Any]:
    config = node.get("config") or node.get("data") or {}
    node_id = node["id"]
    tool_name = config.get("toolName") or config.get("tool_name") or "calculator"
    tool_input: dict[str, Any] = dict(node_input) if isinstance(node_input, dict) else {}
    for key in ("expression", "query", "input"):
        if config.get(key) is not None:
            tool_input[key] = config[key]

    emitter.emit("tool_called", "running", node_id=node_id, tool_name=tool_name,
                 metadata={"input_summary": str(tool_input)[:200]})
    try:
        result = _run_tool(tool_name, tool_input)
    except Exception as exc:  # noqa: BLE001 - surface tool failures as trace events
        emitter.emit("tool_failed", "failed", node_id=node_id, tool_name=tool_name,
                     error_message=str(exc), latency_ms=1)
        raise
    emitter.emit("tool_completed", "success", node_id=node_id, tool_name=tool_name,
                 latency_ms=1, metadata={"result_summary": str(result)[:200]})
    return {"type": "tool_output", "node_id": node_id, "tool_name": tool_name, "result": result}


def _node_input(node: dict, preds: dict, outputs: dict, workflow_input: dict) -> Any:
    if node["type"] == "input":
        return workflow_input
    sources = [s for s in preds.get(node["id"], []) if s in outputs]
    if not sources:
        return workflow_input
    if len(sources) == 1:
        return outputs[sources[0]]
    return {s: outputs[s] for s in sources}


def _execute_graph(graph: dict, run: WorkflowRun, emitter: DemoTraceEmitter,
                   max_steps: int, max_runtime_s: float, settings: Any) -> Any:
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    nodes_by_id = {n["id"]: n for n in nodes}
    order = _topological_order(nodes, edges)
    preds = _predecessors(edges)
    outputs: dict[str, Any] = {}
    workflow_input = run.input_json or {}

    started = time.monotonic()
    steps = 0
    for node_id in order:
        steps += 1
        if steps > max_steps:
            raise ValueError(f"Run exceeded max steps ({max_steps}).")
        if time.monotonic() - started > max_runtime_s:
            raise ValueError(f"Run exceeded max runtime ({max_runtime_s}s).")

        node = nodes_by_id[node_id]
        node_in = _node_input(node, preds, outputs, workflow_input)
        emitter.emit("node_started", "running", node_id=node_id)
        node_start = time.monotonic()
        try:
            if node["type"] == "agent":
                out = _execute_agent(node, node_in, emitter, settings)
            elif node["type"] == "tool":
                out = _execute_tool(node, node_in, emitter)
            else:  # input / router / output — pass-through in the demo
                out = node_in if isinstance(node_in, dict) else {"value": node_in}
        except Exception as exc:
            latency = int((time.monotonic() - node_start) * 1000)
            emitter.emit("node_failed", "failed", node_id=node_id,
                         error_message=str(exc), latency_ms=latency)
            raise
        outputs[node_id] = out
        latency = int((time.monotonic() - node_start) * 1000)
        emitter.emit("node_completed", "success", node_id=node_id, latency_ms=latency,
                     metadata={"output_type": out.get("type") if isinstance(out, dict) else "value"})

    output_nodes = [n for n in nodes if n["type"] == "output"]
    if len(output_nodes) == 1:
        return outputs.get(output_nodes[0]["id"], {})
    if output_nodes:
        return {n["id"]: outputs.get(n["id"], {}) for n in output_nodes}
    # No explicit output node — return the last node's output.
    return outputs.get(order[-1], {}) if order else {}


def _aggregate_totals(emitter: DemoTraceEmitter) -> tuple[int, int, float]:
    in_tok = sum(e.input_tokens for e in emitter.events if e.event_type == "model_completed")
    out_tok = sum(e.output_tokens for e in emitter.events if e.event_type == "model_completed")
    cost = sum(e.estimated_cost_usd for e in emitter.events if e.event_type == "model_completed")
    return in_tok, out_tok, round(cost, 8)


def execute_demo_run_with_session(
    db: Session,
    run: WorkflowRun,
    store: TraceStore,
    *,
    settings: Any,
    redis_client: Any | None = None,
) -> WorkflowRun:
    """Core demo execution against a provided session/store (testable).

    Updates the run status/aggregates, streams events to Redis (best-effort),
    persists trace events to the store, and records usage.
    """
    emitter = DemoTraceEmitter(run, redis_client)

    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    db.commit()
    emitter.emit("run_started", "running")

    start = time.monotonic()
    try:
        version = db.get(WorkflowVersion, run.workflow_version_id)
        if version is None:
            raise ValueError("Workflow version not found.")
        output = _execute_graph(
            version.graph_json or {},
            run,
            emitter,
            max_steps=settings.default_max_steps,
            max_runtime_s=float(settings.default_max_runtime_seconds),
            settings=settings,
        )
        in_tok, out_tok, cost = _aggregate_totals(emitter)
        run.status = "completed"
        run.output_json = output if isinstance(output, dict) else {"result": output}
        run.total_input_tokens = in_tok
        run.total_output_tokens = out_tok
        run.estimated_cost_usd = cost
        run.total_latency_ms = int((time.monotonic() - start) * 1000)
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        emitter.emit("run_completed", "success", latency_ms=run.total_latency_ms)
        logger.info("demo run %s completed", run.id)
    except Exception as exc:  # noqa: BLE001 - never crash the background task
        latency = int((time.monotonic() - start) * 1000)
        run.status = "failed"
        run.error_message = str(exc)
        run.total_latency_ms = latency
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        emitter.emit("run_failed", "failed", error_message=str(exc), latency_ms=latency)
        logger.warning("demo run %s failed: %s", run.id, exc)

    # Persist trace events durably (so run detail/diff/eval work after completion).
    try:
        store.ensure_ready()
        store.insert_events(emitter.events)
    except Exception:  # noqa: BLE001 - trace storage is best-effort
        logger.warning("failed to store demo trace events", exc_info=True)

    # Record usage (idempotent, best-effort) from the in-memory events.
    try:
        usage_service.record_run_usage(db, run, emitter.as_usage_dicts())
    except Exception:  # noqa: BLE001
        logger.warning("failed to record demo usage", exc_info=True)

    return run


def execute_demo_run(run_id: uuid.UUID | str) -> None:
    """Execute a run end-to-end in-process (hosted demo). Safe & best-effort.

    Opens its own DB session (the request session is already closed when this runs
    as a background task), then delegates to ``execute_demo_run_with_session``.
    """
    settings = get_settings()
    run_uuid = run_id if isinstance(run_id, uuid.UUID) else uuid.UUID(str(run_id))

    # Redis is optional — used only for live WS streaming. Tolerate its absence.
    redis_client: Any | None = None
    try:
        from app.db.redis import get_redis

        redis_client = get_redis()
    except Exception:  # noqa: BLE001
        logger.debug("Redis unavailable for demo run; live streaming disabled", exc_info=True)

    with SessionLocal() as db:
        run = db.get(WorkflowRun, run_uuid)
        if run is None:
            logger.warning("demo run %s not found", run_uuid)
            return
        store = make_trace_store(db)
        execute_demo_run_with_session(
            db, run, store, settings=settings, redis_client=redis_client
        )
