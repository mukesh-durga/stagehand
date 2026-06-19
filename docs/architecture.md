# Architecture

High-level architecture overview for Stagehand. See `STAGEHAND_PROJECT.md` for the
full product definition and `CLAUDE.md` for coding rules.

## Components

- **Frontend** — React + TypeScript + Vite + React Flow + Zustand + Tailwind + shadcn/ui.
  Visual workflow builder, live trace timeline, run detail, replay, diff.
- **Backend API** — FastAPI + Pydantic + SQLAlchemy/SQLModel. Auth, workflow CRUD,
  run creation, trace retrieval, WebSocket trace gateway.
- **Worker** — Separate Python process running the custom trace-first orchestration
  engine. Consumes run jobs from Redis and executes workflow graphs.
- **PostgreSQL** — Transactional/product data: users, workflows, workflow versions,
  runs, templates, eval results, API keys.
- **ClickHouse** — Append-heavy trace events and analytics (latency, cost, tokens,
  model usage, failures).
- **Redis** — Run job queue, trace event stream, temporary run state, WebSocket fanout.

## Data flow

```
Frontend → REST → FastAPI → create run record (Postgres) + push job (Redis) → return run_id
Worker   → consume job (Redis) → execute engine → emit trace events (Redis + ClickHouse)
Frontend ← WebSocket ← FastAPI ← subscribe trace stream (Redis)
```

## Key constraint

Workflows are **never** executed inside an API request handler. The API only creates
a run record and enqueues a job; the worker executes asynchronously and emits trace
events that the frontend watches live over WebSocket.

## Diagram

See section 4 of `STAGEHAND_PROJECT.md` for the full ASCII architecture diagram.
