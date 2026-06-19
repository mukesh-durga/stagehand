# Database

Placeholder. See sections 9 (PostgreSQL) and 10 (ClickHouse) of
`STAGEHAND_PROJECT.md` for the full design.

## PostgreSQL (transactional)

Tables: `users`, `organizations`, `projects`, `workflows`, `workflow_versions`,
`workflow_runs`, `eval_results`, `templates`, `api_keys`.

Managed via Alembic migrations starting in Milestone 1.

## ClickHouse (analytics)

Table: `trace_events` (defined in `infra/clickhouse/schema.sql`).

Append-heavy, time-series-like trace data partitioned by month and ordered by
`(workflow_id, run_id, timestamp)`.

This document will be filled in as schema is implemented.
