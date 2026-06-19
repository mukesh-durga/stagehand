-- Stagehand ClickHouse trace schema
-- Loaded at container init. Trace events are append-heavy analytical data:
-- one row per execution event emitted by the worker engine (Milestone 7+).
--
-- Id columns are String (not UUID) so inserts/reads use plain strings end to end,
-- avoiding driver UUID-conversion edge cases. The same DDL is applied idempotently
-- by the worker and API via CREATE TABLE IF NOT EXISTS.

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
ORDER BY (workflow_id, run_id, timestamp);
