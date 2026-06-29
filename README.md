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
├── docker-compose.yml     # postgres, redis, clickhouse (local dev)
├── render.yaml            # Render Blueprint (API + worker)
├── Makefile               # convenience commands
├── scripts/               # deploy_api.sh, start_worker.sh
├── apps/
│   ├── web/               # frontend (Vite/React) + vercel.json
│   ├── api/               # FastAPI backend + Dockerfile
│   └── worker/            # worker engine + Dockerfile
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
| GET | `/health` | Liveness — always ok if the process is up (use as cloud health check) |
| GET | `/health/db` | Readiness — checks PostgreSQL connectivity |
| GET | `/health/redis` | Readiness — checks Redis connectivity |
| GET | `/health/clickhouse` | Readiness — checks ClickHouse connectivity |
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
| GET | `/routing/stats` | Adaptive-routing (UCB) stats, optionally filtered |
| GET | `/routing/stats/{route_key}` | Routing stats for one route key |
| POST | `/routing/stats/reset` | Dev helper: clear all routing stats |
| GET | `/templates` | List public workflow templates |
| GET | `/templates/{slug}` | Get one template |
| POST | `/templates/{slug}/clone` | Clone a template into a new editable workflow |
| GET | `/usage/events` | Recent usage events (optional `run_id`/`workflow_id`/`event_type`) |
| GET | `/usage/summary` | Aggregate usage (runs, calls, tokens, cost breakdowns) |
| POST | `/usage/backfill` | Idempotently record usage for completed runs |
| GET | `/billing/status` | Billing mode (`mock` / `stripe_test`) |
| POST | `/billing/create-checkout-session` | Test/mock checkout (never a real charge) |
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
`/runs`, `/runs/:runId`, `/templates`, `/routing`, `/usage`, `/settings`. The dashboard
calls `/health` and `/health/db` and shows API/DB status. `/usage` is a SaaS-style
usage dashboard (runs, model/tool calls, tokens, cost, cost-by-model, events) with a
**Backfill usage** button and a billing card. Billing is **test mode only** — `mock`
when no Stripe key, `stripe_test` with a `sk_test_...` key; no real charges ever. `/templates` is the gallery —
clone a seeded template (Basic Agent, Tool Calculator, Agent With Retry, Adaptive
Agent) into a new editable workflow that opens in the builder. `/runs/:runId` is the run detail page (status, metrics,
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

An agent node's `modelPolicy` selects the model: `cheap`/`strong` use the configured
model directly; **`adaptive`** uses a **UCB bandit** (`worker/ai/ucb_router.py`) that
picks between the cheap and strong models per route (`workflow:version:node`),
emitting a `routing_decision` trace event. When a run is evaluated, its reward
(`0.7·quality + 0.2·latency + 0.1·cost`) updates `model_routing_stats` (once per run).
The `/routing` page shows per-model pulls, average reward, latency, cost, and quality.

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

## Production deployment

Stagehand is **local-first** but deployment-ready. The reference topology:

| Component | Host |
|---|---|
| Frontend | Vercel (`apps/web`, Vite static build) |
| API | Render (`apps/api/Dockerfile`, web service) |
| Worker | Render (`apps/worker/Dockerfile`, background worker) |
| PostgreSQL | Neon / Supabase (`DATABASE_URL`) |
| Redis | Upstash (`REDIS_URL`) |
| ClickHouse | ClickHouse Cloud (`CLICKHOUSE_*`, `CLICKHOUSE_SECURE=true`) |

- One-click infra via the [`render.yaml`](./render.yaml) Blueprint (API + worker).
  Railway and Fly.io use the same Dockerfiles.
- Frontend deploy config in [`apps/web/vercel.json`](./apps/web/vercel.json).
- Manual deploy helpers: [`scripts/deploy_api.sh`](./scripts/deploy_api.sh)
  (installs deps → `alembic upgrade head` → uvicorn) and
  [`scripts/start_worker.sh`](./scripts/start_worker.sh).
- Cloud health check path is `/health`; DB/Redis/ClickHouse readiness at
  `/health/db`, `/health/redis`, `/health/clickhouse`.

**Full step-by-step guide, env-var tables, smoke test, and troubleshooting:
[`docs/deployment.md`](./docs/deployment.md).** No secrets are committed — every
cloud secret is set in the provider dashboard (`.env` is git-ignored;
`.env.example` holds placeholders only).

### Free Hosted Demo Mode (no-cost)

Set `DEPLOYMENT_MODE=hosted_demo` to run a public demo entirely on free tiers —
**no paid ClickHouse and no always-on worker.** In this mode ClickHouse is disabled
(traces are stored in PostgreSQL via `trace_events_pg`), the separate worker is not
needed (the API executes short, mock-only runs in a background task), and AI/billing
are mock. `/health/clickhouse` returns `disabled` (never failing a deploy health
check). Local full-stack mode (Docker Compose + worker + ClickHouse) is unchanged.
The flags `CLICKHOUSE_ENABLED` / `WORKER_ENABLED` / `HOSTED_DEMO_EXECUTION` /
`TRACE_STORAGE` default from `DEPLOYMENT_MODE` and can be overridden individually.
See [Free Hosted Demo Mode](./docs/deployment.md#h-free-hosted-demo-mode-no-cost-linkedin-demo).

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
- [x] **Milestone 15** — UCB model router (`model_routing_stats`, UCB selection, `routing_decision` traces, `/routing` dashboard)
- [x] **Milestone 16** — Template gallery (`templates` table, startup seed, gallery page, clone-to-workflow)
- [x] **Milestone 17** — Usage tracking + mock/Stripe-test billing (`usage_events`, `/usage` dashboard)
- [x] **Milestone 18** — Deployment readiness (Dockerfiles, `render.yaml`, `vercel.json`, prod env/CORS/WS config, deploy docs)
- [x] **Milestone 18.5** — Free hosted demo mode (deployment-mode flags, Postgres trace fallback + TraceStore abstraction, in-API mock executor, ClickHouse-optional health)
