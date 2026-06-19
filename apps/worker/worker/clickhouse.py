"""ClickHouse client + trace inserts for the worker."""

import json
import logging
from datetime import timezone
from functools import lru_cache
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from worker.config import get_settings
from worker.engine.trace import TraceEvent

logger = logging.getLogger(__name__)

TRACE_TABLE = "trace_events"

TRACE_COLUMNS = [
    "event_id",
    "run_id",
    "workflow_id",
    "workflow_version_id",
    "node_id",
    "event_type",
    "status",
    "timestamp",
    "latency_ms",
    "model_name",
    "input_tokens",
    "output_tokens",
    "estimated_cost_usd",
    "tool_name",
    "retry_count",
    "error_message",
    "metadata_json",
]

CREATE_TRACE_TABLE = """
CREATE TABLE IF NOT EXISTS trace_events (
    event_id String,
    run_id String,
    workflow_id String,
    workflow_version_id String,
    node_id String,
    event_type String,
    status String,
    timestamp DateTime64(3),
    latency_ms UInt64,
    model_name String,
    input_tokens UInt64,
    output_tokens UInt64,
    estimated_cost_usd Float64,
    tool_name String,
    retry_count UInt8,
    error_message String,
    metadata_json String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(timestamp)
ORDER BY (workflow_id, run_id, timestamp)
"""


@lru_cache
def _client() -> Client:
    s = get_settings()
    return clickhouse_connect.get_client(
        host=s.clickhouse_host,
        port=s.clickhouse_port,
        username=s.clickhouse_user,
        password=s.clickhouse_password,
        database=s.clickhouse_database,
    )


def get_clickhouse() -> Client:
    return _client()


def ensure_trace_table(client: Client) -> None:
    client.command(CREATE_TRACE_TABLE)


def _event_to_row(event: TraceEvent) -> list[Any]:
    # Store timestamp as naive UTC for DateTime64; metadata as a JSON string.
    ts = event.timestamp
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return [
        event.event_id,
        event.run_id,
        event.workflow_id,
        event.workflow_version_id,
        event.node_id,
        event.event_type,
        event.status,
        ts,
        int(event.latency_ms),
        event.model_name,
        int(event.input_tokens),
        int(event.output_tokens),
        float(event.estimated_cost_usd),
        event.tool_name,
        int(event.retry_count),
        event.error_message,
        json.dumps(event.metadata_json),
    ]


def insert_trace_event(client: Client, event: TraceEvent) -> None:
    client.insert(TRACE_TABLE, [_event_to_row(event)], column_names=TRACE_COLUMNS)
