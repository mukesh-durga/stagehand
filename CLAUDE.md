# CLAUDE.md

## Project Name

Stagehand — Multi-Agent Workflow Builder with Live Execution Tracing

## Project Purpose

Stagehand is a trace-first full-stack AI workflow platform. Users visually design multi-agent workflows on a canvas, execute them asynchronously, and debug every run through live execution traces, replay, diffing, evals, token/cost analytics, latency analytics, and adaptive model routing.

This is a serious Software Engineer / AI Full-Stack / Backend Systems portfolio project. Build it like a real product, but implement it milestone by milestone.

---

## Source of Truth

Before writing code, always read:

```text
STAGEHAND_PROJECT.md
```

That file contains the full product definition, architecture, build plan, database design, API plan, deployment plan, and interview reasoning.

This `CLAUDE.md` file contains the coding rules and current implementation workflow.

---

## Important Behavior Rules

1. Do not build everything at once.
2. Implement one milestone at a time.
3. Before coding a milestone, explain what files will be created or changed.
4. After coding, summarize exactly what changed.
5. Do not rewrite unrelated files.
6. Do not introduce unnecessary complexity.
7. Prefer simple, working, typed, testable code.
8. Add tests for backend services, worker engine logic, and critical frontend behavior.
9. Do not fake completed features.
10. Do not claim metrics such as cost reduction unless benchmark code and results exist.
11. Keep code clean enough for a resume/project demo.
12. Keep all secrets in `.env`; never hard-code API keys.
13. Update README or docs when setup steps change.
14. If a decision is unclear, choose the simpler MVP option and document it.
15. Do not use paid services unless the project explicitly reaches deployment milestone.

---

## Architecture Rules

Stagehand must follow this architecture:

```text
Frontend:
React + TypeScript + Vite + React Flow + Zustand + Tailwind + shadcn/ui

Backend API:
FastAPI + Pydantic + SQLAlchemy/SQLModel + PostgreSQL

Async Execution:
Redis queue/streams + separate Python worker process

Realtime:
FastAPI WebSockets + Redis event fanout

Trace Storage:
ClickHouse for trace events and analytics

Workflow Storage:
PostgreSQL for users, projects, workflows, workflow versions, runs, templates, eval results

AI Layer:
Custom lightweight orchestration engine with model provider abstraction

Deployment:
Frontend on Vercel
Backend/worker on Render, Fly.io, or Railway
Postgres on Neon/Supabase
Redis on Upstash
ClickHouse local first, ClickHouse Cloud later
```

---

## Non-Negotiable Design Constraints

### 1. Do not execute workflows inside the API request handler

Bad:

```text
POST /run waits until the full workflow finishes.
```

Good:

```text
POST /run creates a run record, pushes job to Redis, returns run_id.
Worker executes the run asynchronously.
Frontend watches progress over WebSocket.
```

### 2. Every workflow run must emit trace events

At minimum:

```text
run_started
node_started
node_completed
node_failed
run_completed
run_failed
```

Later:

```text
model_called
model_completed
tool_called
tool_completed
retry_scheduled
fallback_used
eval_started
eval_completed
```

### 3. PostgreSQL and ClickHouse have separate responsibilities

Use PostgreSQL for product/transactional data:

```text
users
projects
workflows
workflow_versions
workflow_runs
templates
eval_results
api_keys
```

Use ClickHouse for trace/event analytics:

```text
trace_events
model usage
tool calls
latency analytics
cost analytics
failure analytics
```

### 4. Redis is required for async execution

Use Redis for:

```text
workflow run queue
trace event stream
temporary run status
WebSocket fanout
```

### 5. The orchestration engine must be custom and trace-first

Do not blindly use LangGraph as the main engine. The purpose of this project is to build a lightweight custom engine that exposes execution internals clearly.

The engine should include:

```text
WorkflowLoader
WorkflowValidator
ExecutionPlanner
ExecutionContext
Orchestrator
NodeExecutor
AgentNodeExecutor
ToolNodeExecutor
RouterNodeExecutor
OutputNodeExecutor
TraceEmitter
RetryManager
ModelRouter
EvalRunner
```

---

## Security Rules

1. Never expose API keys to the frontend.
2. Store secrets only in environment variables or encrypted backend storage.
3. Validate all API inputs with Pydantic.
4. Validate all tool inputs with schemas.
5. Each agent must have an explicit tool allowlist.
6. No arbitrary shell execution tools in MVP.
7. Add max steps per run.
8. Add max runtime per run.
9. Add max cost per run.
10. Add max retries per node.
11. Add timeouts for model calls and tool calls.
12. Add workflow ownership checks once auth exists.
13. Add rate limits before public demo.
14. Do not allow model output to modify tool permissions.
15. Do not send secrets to LLM providers.

---

## AI Rules

Use a provider abstraction. Do not tightly couple the system to one model vendor.

Initial model strategy:

```text
cheap_model:
routing, classification, simple summaries, simple extraction

strong_model:
complex reasoning, final synthesis, LLM-as-judge eval, fallback
```

Model names must come from environment variables:

```env
CHEAP_MODEL_NAME=
STRONG_MODEL_NAME=
DEFAULT_EVAL_MODEL_NAME=
```

Provider keys must come from environment variables:

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

Model responses should always capture:

```text
text
model_name
input_tokens
output_tokens
estimated_cost_usd
latency_ms
raw_response optional
```

---

## Tool Calling Rules

Every tool must have:

```text
name
description
input schema
output schema
timeout
executor
```

MVP tools:

```text
calculator
mock_search
document_search
summarizer
```

Do not add unrestricted web browsing, shell tools, or arbitrary code execution in MVP.

Every tool call must emit trace events:

```text
tool_called
tool_completed
tool_failed
```

---

## Eval Harness Rules

Do not build UCB bandit before eval harness.

Correct order:

```text
1. Tracing
2. Replay
3. Diff
4. Eval harness
5. UCB model routing
```

Eval types to support:

```text
exact_match
json_schema
tool_usage
latency
cost
llm_as_judge
```

Eval result should include:

```text
success_score
tool_correctness_score
format_score
quality_score
cost_score
latency_score
metadata
```

---

## UCB Bandit Rules

Only implement adaptive model routing after the benchmark/eval system exists.

UCB formula:

```text
UCB(model) = average_reward(model) + c * sqrt(log(total_trials) / trials_for_model)
```

Recommended reward:

```text
reward = 0.7 * quality_score + 0.2 * latency_score + 0.1 * cost_score
```

Do not claim cost reduction until benchmark results are generated.

---

## Build Milestones

Follow this exact order.

### Milestone 0 — Repo Setup

Create:

```text
README.md
PROJECT.md or keep STAGEHAND_PROJECT.md
CLAUDE.md
.env.example
.gitignore
docker-compose.yml
Makefile
apps/web
apps/api
apps/worker
infra
docs
```

Acceptance criteria:

```text
Repo structure exists.
Docker services for Postgres, Redis, and ClickHouse can start.
README explains local setup.
```

---

### Milestone 1 — Backend Foundation

Build:

```text
FastAPI app
config loading
health endpoint
Postgres connection
Alembic migrations
basic tests
```

Acceptance criteria:

```text
GET /health returns OK.
Postgres connection works.
Tests pass.
```

---

### Milestone 2 — Workflow CRUD

Build:

```text
workflow model
workflow_versions model
Pydantic schemas
POST /workflows
GET /workflows
GET /workflows/{workflow_id}
PUT /workflows/{workflow_id}
graph validation
```

Acceptance criteria:

```text
Can create workflow.
Can save graph JSON.
Can load workflow.
Invalid graph is rejected.
```

---

### Milestone 3 — Frontend Foundation

Build:

```text
Vite React TypeScript app
Tailwind
shadcn/ui
routing
dashboard layout
API client
Zustand store
```

Acceptance criteria:

```text
Frontend runs locally.
Dashboard renders.
Frontend can call backend health endpoint.
```

---

### Milestone 4 — React Flow Builder

Build:

```text
React Flow canvas
node sidebar
custom nodes
drag/drop node creation
edge connection
node configuration panel
save/load workflow
```

Acceptance criteria:

```text
User can visually create workflow.
User can save workflow.
User can reload workflow.
```

---

### Milestone 5 — Redis Queue and Run Creation

Build:

```text
workflow_runs table
POST /workflows/{workflow_id}/run
create run record
push run job to Redis
return run_id
```

Acceptance criteria:

```text
Clicking run creates queued run.
Run job appears in Redis.
```

---

### Milestone 6 — Worker and Basic Engine

Build:

```text
worker process
Redis job consumer
workflow loader
workflow validator
execution context
basic topological execution
input node
output node
run status updates
```

Acceptance criteria:

```text
Worker picks queued run.
Run moves queued -> running -> completed.
Output is stored.
```

---

### Milestone 7 — Trace Event Pipeline

Build:

```text
TraceEvent schema
TraceEmitter
Redis trace publishing
ClickHouse trace table
ClickHouse insertion
trace retrieval API
```

Acceptance criteria:

```text
Each run emits trace events.
Trace events are stored in ClickHouse.
Trace events can be fetched through API.
```

---

### Milestone 8 — WebSocket Live Tracing

Build:

```text
WS /ws/runs/{run_id}
Redis event subscription
frontend WebSocket client
live trace timeline
canvas node status highlighting
```

Acceptance criteria:

```text
User sees live events while workflow executes.
Active/completed/failed nodes are highlighted.
```

---

### Milestone 9 — Agent and Tool Nodes

Build:

```text
ModelProvider abstraction
AgentNodeExecutor
ToolNodeExecutor
calculator tool
mock_search tool
model trace events
tool trace events
```

Acceptance criteria:

```text
Agent node can call model.
Tool node can call safe tool.
Trace shows model/tool details.
```

---

### Milestone 10 — Retry and Fallback

Build:

```text
RetryManager
max retry config
timeout handling
fallback model
retry_scheduled trace
fallback_used trace
UI retry/fallback display
```

Acceptance criteria:

```text
Failed calls retry.
Fallback model works.
Trace shows retry and fallback.
```

---

### Milestone 11 — Run Detail Page

Build:

```text
/runs/:runId page
run metadata view
trace timeline
metrics summary
node detail panel
```

Acceptance criteria:

```text
Completed runs can be inspected.
User can see cost, tokens, latency, model, tool, retries, and errors.
```

---

### Milestone 12 — Replay

Build:

```text
POST /runs/{run_id}/replay
copy original workflow version
copy original input
link original and replay run
replay UI
```

Acceptance criteria:

```text
User can replay previous run.
Replay run is linked to original run.
```

---

### Milestone 13 — Diff

Build:

```text
diff service
GET /runs/{run_id}/diff/{other_run_id}
node-by-node comparison
diff UI
```

Compare:

```text
status
model used
tool used
tokens
cost
latency
retry count
fallback usage
error message
eval score
```

Acceptance criteria:

```text
User can compare two runs.
UI shows meaningful differences.
```

---

### Milestone 14 — Eval Harness

Build:

```text
eval_results table
exact match eval
JSON schema eval
tool usage eval
cost eval
latency eval
LLM-as-judge eval
POST /runs/{run_id}/eval
eval result UI
```

Acceptance criteria:

```text
Run receives success score.
Eval result is stored and visible.
```

---

### Milestone 15 — UCB Model Router

Build:

```text
model_routing_stats table
reward function
UCB selection logic
adaptive routing policy
routing decision traces
model routing dashboard
```

Acceptance criteria:

```text
Adaptive router chooses cheap/strong models.
Routing decisions are visible in trace.
Cost/quality metrics are measurable.
```

---

### Milestone 16 — Template Gallery

Build:

```text
templates table
seed templates
template gallery page
clone template to workflow
shareable workflow URL
```

Acceptance criteria:

```text
User can create workflow from template.
User can share workflow.
```

---

### Milestone 17 — Stripe Test Mode

Build:

```text
usage events
usage dashboard
Stripe test customer
Stripe test checkout or billing portal optional
```

Acceptance criteria:

```text
Usage dashboard works.
Stripe test mode works.
No real payments are charged.
```

---

### Milestone 18 — Deployment

Deploy:

```text
Frontend -> Vercel
Backend API -> Render/Fly/Railway
Worker -> Render/Fly/Railway
Postgres -> Neon/Supabase
Redis -> Upstash
ClickHouse -> ClickHouse Cloud or hosted Docker
```

Acceptance criteria:

```text
Live app works.
Workflow can be created.
Workflow can be run.
Live tracing works.
Run detail works.
Replay works.
Diff works.
Demo workflow exists.
```

---

## Initial Folder Structure to Create

```text
stagehand/
  STAGEHAND_PROJECT.md
  CLAUDE.md
  README.md
  .env.example
  .gitignore
  docker-compose.yml
  Makefile

  apps/
    web/
    api/
    worker/

  infra/
    clickhouse/
    postgres/
    docker/

  docs/
    architecture.md
    api.md
    database.md
    deployment.md
    experiments.md
```

---

## Suggested First Claude Code Prompt

Use this prompt first:

```text
Read STAGEHAND_PROJECT.md and CLAUDE.md fully. Do not write code yet. Summarize the architecture, list the build milestones, identify Milestone 0, and propose the exact files/folders you will create first. Wait for my confirmation before making changes.
```

After Claude Code responds, use:

```text
Proceed with Milestone 0 only. Create the repository structure, .env.example, .gitignore, docker-compose.yml, Makefile, README.md, and placeholder app folders. Do not implement backend/frontend logic yet. After creating files, summarize what changed and how to verify it.
```

Then:

```text
Proceed with Milestone 1 only. Implement the FastAPI backend foundation with config loading, health endpoint, Postgres connection setup, Alembic, and basic tests. Do not work on frontend or worker yet. After coding, run tests and summarize results.
```

---

## Definition of Done for Each Milestone

Each milestone is complete only when:

```text
1. Code is implemented.
2. App starts without obvious errors.
3. Relevant tests pass.
4. README or docs are updated if setup changed.
5. No unrelated files were rewritten.
6. The milestone acceptance criteria are satisfied.
7. The next milestone is clearly stated.
```

---

## Final Project Definition

Stagehand is a full-stack, trace-first multi-agent workflow platform that lets users visually design AI workflows, execute them asynchronously, stream every execution event live, store traces for analytics, replay failures, compare runs, evaluate workflow quality, and reduce token cost through adaptive model routing.
