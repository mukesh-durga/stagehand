"""Orchestrates a single workflow run: validate, plan, execute, update status."""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from worker.config import get_settings
from worker.engine.context import ExecutionContext
from worker.engine.errors import (
    EngineError,
    MaxRuntimeExceededError,
    MaxStepsExceededError,
)
from worker.engine.execution_planner import topological_order
from worker.engine.nodes.agent_node import AgentNode
from worker.engine.nodes.base import NodeExecutor
from worker.engine.nodes.input_node import InputNode
from worker.engine.nodes.output_node import OutputNode
from worker.engine.nodes.router_node import RouterNode
from worker.engine.nodes.tool_node import ToolNode
from worker.engine.trace_emitter import TraceEmitter
from worker.engine.workflow_loader import load_workflow_version
from worker.engine.workflow_validator import validate_graph
from worker.models import WorkflowRun

logger = logging.getLogger(__name__)

NODE_REGISTRY: dict[str, NodeExecutor] = {
    "input": InputNode(),
    "agent": AgentNode(),
    "tool": ToolNode(),
    "router": RouterNode(),
    "output": OutputNode(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _predecessors(edges: list[dict[str, Any]]) -> dict[str, list[str]]:
    preds: dict[str, list[str]] = {}
    for edge in edges:
        preds.setdefault(edge["target"], []).append(edge["source"])
    return preds


def _node_input(
    node: dict[str, Any],
    preds: dict[str, list[str]],
    outputs: dict[str, Any],
    workflow_input: dict[str, Any],
) -> Any:
    if node["type"] == "input":
        return workflow_input
    sources = preds.get(node["id"], [])
    available = [outputs[s] for s in sources if s in outputs]
    if not available:
        return workflow_input
    if len(available) == 1:
        return available[0]
    return {s: outputs[s] for s in sources if s in outputs}


def execute_graph(
    graph: dict[str, Any], context: ExecutionContext, emitter: TraceEmitter
) -> Any:
    """Execute a validated graph in topological order; return final output."""
    nodes = graph["nodes"]
    edges = graph.get("edges") or []
    nodes_by_id = {n["id"]: n for n in nodes}

    order = topological_order(nodes, edges)
    preds = _predecessors(edges)

    for node_id in order:
        context.step_count += 1
        if context.step_count > context.max_steps:
            raise MaxStepsExceededError(
                f"Run exceeded max steps ({context.max_steps})."
            )
        if context.elapsed_seconds() > context.max_runtime_seconds:
            raise MaxRuntimeExceededError(
                f"Run exceeded max runtime ({context.max_runtime_seconds}s)."
            )

        node = nodes_by_id[node_id]
        node_input = _node_input(node, preds, context.node_outputs, context.input)
        executor = NODE_REGISTRY[node["type"]]

        emitter.emit_node_started(node_id)
        node_start = time.monotonic()
        try:
            output = executor.execute(node, context, node_input)
        except Exception as exc:
            latency_ms = int((time.monotonic() - node_start) * 1000)
            emitter.emit_node_failed(node_id, str(exc), latency_ms)
            raise
        latency_ms = int((time.monotonic() - node_start) * 1000)
        context.node_outputs[node_id] = output
        emitter.emit_node_completed(
            node_id,
            latency_ms,
            metadata={
                "output_type": output.get("type") if isinstance(output, dict) else type(output).__name__
            },
        )

    output_nodes = [n for n in nodes if n["type"] == "output"]
    if len(output_nodes) == 1:
        return context.node_outputs[output_nodes[0]["id"]]
    return {n["id"]: context.node_outputs[n["id"]] for n in output_nodes}


def _resolve_limits(run_config: dict[str, Any] | None) -> tuple[int, int, float]:
    settings = get_settings()
    rc = run_config or {}
    max_steps = rc.get("max_steps") or settings.default_max_steps
    max_runtime = rc.get("max_runtime_seconds") or settings.default_max_runtime_seconds
    max_cost = rc.get("max_cost_usd") or settings.default_max_cost_usd
    return int(max_steps), int(max_runtime), float(max_cost)


def execute_run(
    db: Session,
    run: WorkflowRun,
    run_config: dict[str, Any] | None = None,
    emitter: TraceEmitter | None = None,
) -> WorkflowRun:
    """Execute a queued run end to end, updating its status and output.

    When no ``emitter`` is supplied a sink-less one is used (events are recorded
    but not published/persisted) — production callers pass an emitter wired to
    Redis and ClickHouse.
    """
    if emitter is None:
        emitter = TraceEmitter.from_run(run)

    max_steps, max_runtime, max_cost = _resolve_limits(run_config)

    run.status = "running"
    run.started_at = _now()
    db.commit()
    emitter.emit_run_started()

    start = time.monotonic()
    try:
        version = load_workflow_version(db, run.workflow_version_id)
        graph = version.graph_json
        validate_graph(graph)

        context = ExecutionContext(
            run_id=str(run.id),
            workflow_id=str(run.workflow_id),
            workflow_version_id=str(run.workflow_version_id),
            input=run.input_json or {},
            run_config=run_config or {},
            max_steps=max_steps,
            max_runtime_seconds=max_runtime,
            max_cost_usd=max_cost,
        )
        output = execute_graph(graph, context, emitter)

        run.status = "completed"
        run.output_json = output if isinstance(output, dict) else {"result": output}
        run.completed_at = _now()
        run.total_latency_ms = int((time.monotonic() - start) * 1000)
        db.commit()
        emitter.emit_run_completed(run.total_latency_ms)
        logger.info("run %s completed", run.id)
    except EngineError as exc:
        latency_ms = _mark_failed(db, run, str(exc), start)
        emitter.emit_run_failed(str(exc), latency_ms)
        logger.warning("run %s failed: %s", run.id, exc)
    except Exception as exc:  # noqa: BLE001 - never let the worker crash on a job
        latency_ms = _mark_failed(db, run, f"Unexpected error: {exc}", start)
        emitter.emit_run_failed(f"Unexpected error: {exc}", latency_ms)
        logger.exception("run %s failed unexpectedly", run.id)

    return run


def _mark_failed(db: Session, run: WorkflowRun, message: str, start: float) -> int:
    latency_ms = int((time.monotonic() - start) * 1000)
    run.status = "failed"
    run.error_message = message
    run.completed_at = _now()
    run.total_latency_ms = latency_ms
    db.commit()
    return latency_ms
