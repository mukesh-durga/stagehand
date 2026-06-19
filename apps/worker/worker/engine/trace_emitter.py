"""TraceEmitter: builds trace events, publishes to Redis, inserts into ClickHouse.

Trace persistence is best-effort: a failing Redis publish or ClickHouse insert is
logged and swallowed so it never crashes a workflow run. Every emitted event is
also recorded on ``self.events`` (useful for tests and debugging).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from worker.engine.trace import TraceEvent, run_events_key

logger = logging.getLogger(__name__)


class TraceEmitter:
    def __init__(
        self,
        run_id: Any,
        workflow_id: Any,
        workflow_version_id: Any,
        *,
        redis_client: Any | None = None,
        clickhouse_client: Any | None = None,
    ) -> None:
        self.run_id = str(run_id)
        self.workflow_id = str(workflow_id)
        self.workflow_version_id = str(workflow_version_id)
        self.redis_client = redis_client
        self.clickhouse_client = clickhouse_client
        self.events: list[TraceEvent] = []

    @classmethod
    def from_run(
        cls,
        run: Any,
        *,
        redis_client: Any | None = None,
        clickhouse_client: Any | None = None,
    ) -> "TraceEmitter":
        return cls(
            run.id,
            run.workflow_id,
            run.workflow_version_id,
            redis_client=redis_client,
            clickhouse_client=clickhouse_client,
        )

    def emit(
        self,
        event_type: str,
        status: str,
        *,
        node_id: str = "",
        latency_ms: int = 0,
        error_message: str = "",
        metadata: dict[str, Any] | None = None,
        model_name: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        tool_name: str = "",
        retry_count: int = 0,
    ) -> TraceEvent:
        event = TraceEvent(
            event_id=str(uuid.uuid4()),
            run_id=self.run_id,
            workflow_id=self.workflow_id,
            workflow_version_id=self.workflow_version_id,
            node_id=node_id,
            event_type=event_type,
            status=status,
            timestamp=datetime.now(timezone.utc),
            latency_ms=latency_ms,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            tool_name=tool_name,
            retry_count=retry_count,
            error_message=error_message,
            metadata_json=metadata or {},
        )
        self.events.append(event)
        self._publish(event)
        self._store(event)
        return event

    def _publish(self, event: TraceEvent) -> None:
        if self.redis_client is None:
            return
        try:
            self.redis_client.rpush(
                run_events_key(self.run_id), event.model_dump_json()
            )
        except Exception:  # noqa: BLE001 - trace publish is best-effort
            logger.warning("failed to publish trace event to Redis", exc_info=True)

    def _store(self, event: TraceEvent) -> None:
        if self.clickhouse_client is None:
            return
        try:
            # Imported lazily so the engine has no hard dependency on ClickHouse.
            from worker.clickhouse import insert_trace_event

            insert_trace_event(self.clickhouse_client, event)
        except Exception:  # noqa: BLE001 - trace storage is best-effort
            logger.warning("failed to insert trace event into ClickHouse", exc_info=True)

    # --- typed helpers ---

    def emit_run_started(self) -> TraceEvent:
        return self.emit("run_started", "running")

    def emit_node_started(self, node_id: str) -> TraceEvent:
        return self.emit("node_started", "running", node_id=node_id)

    def emit_node_completed(
        self, node_id: str, latency_ms: int, metadata: dict[str, Any] | None = None
    ) -> TraceEvent:
        return self.emit(
            "node_completed", "success", node_id=node_id, latency_ms=latency_ms, metadata=metadata
        )

    def emit_node_failed(
        self, node_id: str, error_message: str, latency_ms: int = 0
    ) -> TraceEvent:
        return self.emit(
            "node_failed",
            "failed",
            node_id=node_id,
            error_message=error_message,
            latency_ms=latency_ms,
        )

    def emit_run_completed(self, latency_ms: int) -> TraceEvent:
        return self.emit("run_completed", "success", latency_ms=latency_ms)

    def emit_run_failed(self, error_message: str, latency_ms: int = 0) -> TraceEvent:
        return self.emit(
            "run_failed", "failed", error_message=error_message, latency_ms=latency_ms
        )
