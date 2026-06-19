"""ClickHouse client + trace queries for the API (read path)."""

from functools import lru_cache
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.config import get_settings

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

_TRACE_QUERY = (
    "SELECT " + ", ".join(TRACE_COLUMNS) + " FROM trace_events "
    "WHERE run_id = {run_id:String} ORDER BY timestamp ASC"
)


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
    """FastAPI dependency returning a shared ClickHouse client."""
    return _client()


def ensure_trace_table(client: Client) -> None:
    client.command(CREATE_TRACE_TABLE)


def query_run_trace_events(client: Client, run_id: str) -> list[tuple[Any, ...]]:
    result = client.query(_TRACE_QUERY, parameters={"run_id": run_id})
    return list(result.result_rows)
