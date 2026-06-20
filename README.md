# Stagehand

**Multi-Agent Workflow Builder with Live Execution Tracing**

Stagehand is a trace-first full-stack AI workflow platform. Users visually design
multi-agent workflows on a canvas, execute them asynchronously, and debug every run
through live execution traces, replay, diffing, evals, token/cost analytics, latency
analytics, and adaptive model routing.

- Full product definition & build plan: [`STAGEHAND_PROJECT.md`](./STAGEHAND_PROJECT.md)
- Coding rules & milestone workflow: [`CLAUDE.md`](./CLAUDE.md)
- Docs: [`docs/`](./docs)

## Architecture (overview)

| Layer | Tech |
|---|---|
| Frontend | React + TypeScript + Vite + React Flow + Zustand + Tailwind + shadcn/ui |
| Backend API | FastAPI + Pydantic + SQLAlchemy/SQLModel |
| Worker | Python process running a custom trace-first orchestration engine |
| Realtime | FastAPI WebSockets + Redis fanout |
| Product data | PostgreSQL |
| Trace analytics | ClickHouse |
| Queue / streams | Redis |

Workflows are executed by the worker — never inside an API request handler. Every
node execution emits trace events. See [`docs/architecture.md`](./docs/architecture.md).

## Repository structure

```
stagehand/
├── STAGEHAND_PROJECT.md   # full product/architecture/build plan
├── CLAUDE.md              # coding rules & milestone instructions
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml     # postgres, redis, clickhouse
├── Makefile               # convenience commands
├── apps/
│   ├── web/               # frontend (placeholder until Milestone 3)
│   ├── api/               # FastAPI backend (placeholder until Milestone 1)
│   └── worker/            # worker engine (placeholder until Milestone 6)
├── infra/
│   ├── clickhouse/        # schema.sql (trace_events)
│   ├── postgres/          # init.sql (extensions bootstrap)
│   └── docker/            # reserved for additional Dockerfiles
└── docs/                  # architecture, api, database, deployment, experiments
```

## Prerequisites

- Docker + Docker Compose
- Node.js 20+ (frontend, later milestones)
- Python 3.11+ (backend/worker)

> **Note on Postgres port:** If you already run a local Postgres on `5432`, it will
> shadow the Docker container (which binds the wildcard address). Set
> `POSTGRES_PORT=5433` in your `.env`; Compose maps host `5433 -> container 5432`
> and the API reads the same value.

## Local setup

1. **Clone the repo** and enter it.

2. **Create your env file** from the template:

   ```bash
   make env
   # or: cp .env.example .env
   ```

3. **Start infrastructure services** (Postgres, Redis, ClickHouse):

   ```bash
   make up
   # or: docker compose up -d postgres redis clickhouse
   ```

4. **Verify the services are healthy:**

   ```bash
   make health
   ```

   Expected output:
   - Postgres: `... accepting connections`
   - Redis: `PONG`
   - ClickHouse: `Ok.`

5. **Stop services** when done:

   ```bash
   make down          # stop, keep data
   make nuke          # stop and delete all data volumes
   ```

## Useful Make commands

Run `make help` to list all commands. Highlights:

| Command | Description |
|---|---|
| `make env` | Create `.env` from `.env.example` if missing |
| `make up` | Start Postgres, Redis, ClickHouse |
| `make down` | Stop services (keep data) |
| `make ps` | Show running services |
| `make logs` | Tail service logs |
| `make health` | Check all three services respond |
| `make nuke` | Stop services and delete data volumes |

## Backend API (apps/api)

FastAPI backend foundation (Milestone 1). Requires Python 3.11+.

```bash
cd apps/api
python3.12 -m venv .venv          # use a 3.11+ interpreter
.venv/bin/pip install -e ".[dev]"

# Apply database migrations (Postgres must be running)
.venv/bin/alembic upgrade head

# Run the API
.venv/bin/uvicorn app.main:app --reload --port 8000

# Run tests
.venv/bin/pytest -v
```

Endpoints:

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness — always ok if the process is up |
| GET | `/health/db` | Readiness — checks PostgreSQL connectivity |
| POST | `/workflows` | Create workflow + version 1 |
| GET | `/workflows` | List workflows (with current version) |
| GET | `/workflows/{id}` | Get workflow with current graph |
| PUT | `/workflows/{id}` | Update name/description; new graph creates a version |
| DELETE | `/workflows/{id}` | Delete workflow and its versions |
| GET | `/workflows/{id}/versions` | List versions ordered by number |
| POST | `/workflows/{id}/run` | Create a queued run + enqueue Redis job → `run_id` |
| GET | `/runs` | List recent runs (optional `?workflow_id=`) |
| GET | `/runs/{run_id}` | Get a run by id |
| POST | `/runs/{run_id}/replay` | Re-run with the original version + input; links `replay_of_run_id` |
| GET | `/runs/{run_id}/replays` | Runs that are replays of this run |
| GET | `/runs/{run_id}/diff/{other_run_id}` | Compare two runs (summary, node/event/output diffs) |
| POST | `/runs/{run_id}/eval` | Score a run with evaluators; stores `eval_results` |
| GET | `/runs/{run_id}/evals` | Eval results for a run (newest first) |
| GET | `/runs/{run_id}/trace` | Trace events for a run (from ClickHouse), ordered by time |
| WS | `/ws/runs/{run_id}` | Live trace stream (replays + streams `run:{run_id}:events`) |

## Frontend (apps/web)

React + TypeScript + Vite + Tailwind + Zustand + React Router (Milestone 3). Node 20+.

```bash
cd apps/web
cp .env.example .env          # sets VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev                   # http://localhost:5173
npm run typecheck             # tsc --noEmit
npm run build                 # production build to dist/
```

Routes: `/` → `/dashboard`, `/workflows`, `/workflows/new`, `/workflows/:id/builder`,
`/runs`, `/runs/:runId`, `/settings`. The dashboard calls `/health` and `/health/db`
and shows API/DB status. `/runs/:runId` is the run detail page (status, metrics,
input/output, full trace timeline, and a click-through event detail panel); reach it
from the **Runs** sidebar tab or the **Open run details** link in the builder's live
trace panel after a run.
The builder (`/workflows/new`, `/workflows/:id/builder`) is a React Flow canvas for
designing Input/Agent/Tool/Router/Output nodes, with a node config panel and
save/load wired to the `/workflows` API. Start the backend first.

Save a workflow, then click **Run** in the builder: the frontend creates a run and
opens a WebSocket to `/ws/runs/{run_id}`, streaming live trace events into a bottom
panel and highlighting node status (running/completed/failed) on the canvas as the
worker executes. Start one worker (`python -m worker.main`) for runs to execute.

## Worker (apps/worker)

Consumes run jobs from Redis (`queue:workflow_runs`), loads the workflow version
from Postgres, validates the graph, executes a basic topological pass over the
nodes (Input/Agent/Tool/Router/Output — placeholders for now), and updates the run
status (`queued → running → completed/failed`). Requires Python 3.11+.

```bash
cd apps/worker
python3.12 -m venv .venv          # use a 3.11+ interpreter
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m worker.main   # start consuming (blocks)
.venv/bin/pytest -v               # run tests
```

End-to-end: save a workflow → `POST /workflows/{id}/run` (status `queued`) → start
the worker → run becomes `completed` and `GET /runs/{run_id}` returns `output`.

During execution the worker emits trace events (`run_started`, `node_started`,
`node_completed`/`node_failed`, `run_completed`/`run_failed`, plus `model_called`/
`model_completed` for agent nodes and `tool_called`/`tool_completed`/`tool_failed`
for tool nodes). Each event is pushed to a Redis list `run:{run_id}:events` (for
live streaming) and inserted into the ClickHouse `trace_events` table.

**Agent nodes** call a model provider (default: a deterministic `MockModelProvider`,
so no API keys are required locally; set `OPENAI_API_KEY` + `CHEAP_MODEL_NAME`/
`STRONG_MODEL_NAME` to use OpenAI). **Tool nodes** run safe registered tools
(`calculator` — AST-based arithmetic, no `eval`; `mock_search` — deterministic
results). Set a tool node's `Tool name` and its `Expression`/`Query` in the config
panel.

Model and tool calls are wrapped in a `RetryManager` (per-node `maxRetries`,
`timeoutMs`, exponential backoff). On failure the worker emits `retry_scheduled`
before each retry; if an agent's retries are exhausted and a `fallbackModel` is
set, it emits `fallback_used` and tries the fallback. To exercise this locally,
an agent node's config panel exposes mock-only triggers (**Fail first N calls**,
**Force mock failure**) and a **Fallback model** selector. Fetch a run's trace via
`GET /runs/{run_id}/trace`. Trace persistence is best-effort — a Redis/ClickHouse
outage logs a warning but never fails the run.

> Only run **one** worker at a time locally. A stale `python -m worker.main` left
> running keeps consuming jobs with its old in-memory code — stop old workers
> (`pkill -f worker.main`) before starting a new one after code changes.

## Service ports (defaults)

| Service | Port | Notes |
|---|---|---|
| PostgreSQL | 5432 (or 5433 if local PG conflicts) | |
| Redis | 6379 | |
| ClickHouse | 8123 (HTTP), 9000 (native) | |

## Build status

This project is built milestone-by-milestone (see `CLAUDE.md`).

- [x] **Milestone 0** — Repo setup, Docker Compose, README
- [x] **Milestone 1** — Backend foundation (FastAPI, health endpoint, Postgres, Alembic, tests)
- [x] **Milestone 2** — Workflow CRUD (models, versions, endpoints, graph validation, tests)
- [x] **Milestone 3** — Frontend foundation (Vite, Tailwind, routing, API client, Zustand, health check)
- [x] **Milestone 4** — React Flow builder (canvas, custom nodes, config panel, save/load, validation)
- [x] **Milestone 5** — Redis queue and run creation (workflow_runs, POST run, enqueue, runs API)
- [x] **Milestone 6** — Worker and basic engine (consume jobs, validate, topological execution, status updates)
- [x] **Milestone 7** — Trace event pipeline (emit → Redis + ClickHouse, trace retrieval API)
- [x] **Milestone 8** — WebSocket live tracing (WS endpoint, builder Run button, live panel, node status)
- [x] **Milestone 9** — Agent & tool nodes (model provider abstraction, calculator/mock_search, model/tool trace events)
- [x] **Milestone 10** — Retry & fallback (RetryManager, timeouts, fallback model, retry_scheduled/fallback_used events)
- [x] **Milestone 11** — Run detail page (`/runs`, `/runs/:runId`: metadata, metrics, I/O, trace timeline, event detail)
- [x] **Milestone 12** — Replay (replay endpoint, `replay_of_run_id` linkage, Run Detail replay button + replays list)
- [x] **Milestone 13** — Diff (diff endpoint + service, `/runs/:a/diff/:b` page, original↔replay compare links)
- [x] **Milestone 14** — Eval harness (`eval_results`, 6 evaluators, eval endpoints, Run Detail eval section)
- [ ] **Milestone 15** — UCB model router
