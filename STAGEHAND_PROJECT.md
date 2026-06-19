# Stagehand Project Build Plan

**Project:** Stagehand — Multi-Agent Workflow Builder with Live Execution Tracing  
**Purpose:** Full-stack + AI infrastructure portfolio project  
**Target:** Software Engineer / AI Full-Stack / AI Platform / Backend Systems resume project  
**Primary build environment:** Claude Code  
**Recommended repository files:** `PROJECT.md`, `CLAUDE.md`, `README.md`, `.env.example`, `docker-compose.yml`

---

## 0. How to Use This File in Claude Code

This file is the source-of-truth build plan for Stagehand.

When using Claude Code, keep this file in the root of the repository as:

```text
PROJECT.md
```

Also create a shorter `CLAUDE.md` file for persistent coding instructions. Claude Code uses project memory files such as `CLAUDE.md` as context for future sessions. This `PROJECT.md` should contain full product and architecture details, while `CLAUDE.md` should contain concise coding rules, architecture constraints, and current milestone instructions.

Recommended workflow in Claude Code:

```text
1. Ask Claude Code to read PROJECT.md fully.
2. Ask it to create the repository structure only.
3. Ask it to implement one milestone at a time.
4. After every milestone, ask it to run tests.
5. Ask it to update TODOs and decisions in PROJECT.md or separate docs.
6. Do not ask it to build everything in one prompt.
```

Recommended first Claude Code prompt:

```text
Read PROJECT.md fully. Do not write code yet. Summarize the architecture, identify the first milestone, and propose the initial repository structure. Wait for my confirmation before generating files.
```

Recommended implementation rule:

```text
Implement one milestone at a time. Do not skip tests. Do not introduce large unrelated changes. Prefer simple, working, typed code over over-engineered abstractions.
```

---

# 1. Project Overview

## 1.1 Project Name

**Stagehand: Multi-Agent Workflow Builder with Live Execution Tracing**

## 1.2 One-Line Pitch

Stagehand is a trace-first multi-agent workflow builder where users visually design AI agent workflows, execute them asynchronously, and debug every run through live traces, replay, run diffing, cost analytics, latency analytics, evals, and adaptive model routing.

## 1.3 Simple Explanation

Stagehand lets users:

```text
Build AI workflows visually.
Run them safely.
Watch every step live.
Debug failures.
Replay failed runs.
Compare runs.
Measure quality.
Reduce token cost.
```

## 1.4 Product Analogy

```text
Zapier-style visual workflow builder
+
LangGraph-style agent workflow execution
+
LangSmith/Phoenix-style observability
+
SaaS-style usage dashboard
```

## 1.5 Main Problem Statement

Multi-agent AI workflows are difficult to debug and optimize. Developers often see only the final output, but they cannot easily inspect why an agent selected a specific tool, why a workflow looped, which step failed, which model caused high latency, how token cost accumulated, or whether a cheaper model could have completed the same step.

Stagehand solves this by providing a visual workflow builder and a trace-first execution engine that records and streams every node execution, model call, tool call, retry, fallback, error, token count, cost estimate, latency measurement, and eval result.

## 1.6 Core Goal

The core goal is:

> Make multi-agent workflows observable, debuggable, replayable, evaluable, and cost-aware.

---

# 2. Final Feature Set

Stagehand should eventually include the following features.

## 2.1 Core MVP Features

These must be built first.

```text
1. User can create workflows on a drag-and-drop canvas.
2. User can add Input, Agent, Tool, Router, and Output nodes.
3. User can connect nodes with edges.
4. User can configure node prompts, model policy, allowed tools, retry count, and cost limits.
5. Backend validates and stores workflow definitions.
6. User can run a workflow.
7. Backend executes workflow asynchronously using a worker.
8. Each run emits live trace events over WebSockets.
9. UI shows live run timeline.
10. Trace events show latency, token count, cost, model used, tool decisions, retries, and failures.
11. Trace events are stored for later inspection.
12. User can open a completed run and view all trace details.
```

## 2.2 Debugging Features

Build after MVP.

```text
1. Replay a previous run.
2. Compare two runs.
3. Show run diff:
   - model selected
   - tool selected
   - node output
   - latency
   - cost
   - retry count
   - error reason
   - eval score
4. Show failed step clearly.
5. Show fallback path.
6. Show cost-heavy nodes.
7. Show slow nodes.
```

## 2.3 AI Quality Features

Build after trace and replay.

```text
1. Eval harness for workflow runs.
2. Exact-match eval.
3. JSON-schema eval.
4. Tool-usage eval.
5. LLM-as-judge eval.
6. Success score per run.
7. Benchmark workflow suite.
8. Cost/quality dashboard.
```

## 2.4 Cost Optimization Features

Build after eval harness.

```text
1. Cheap model vs strong model routing.
2. UCB bandit model router.
3. Reward function based on quality, cost, and latency.
4. Model usage analytics.
5. Cost reduction experiment.
6. Benchmark report.
```

## 2.5 SaaS Polish Features

Build last.

```text
1. Template gallery.
2. Shareable workflow URLs.
3. Usage dashboard.
4. Stripe test-mode billing.
5. Team/org support.
6. Public demo mode with run limits.
```

---

# 3. Recommended Tech Stack

## 3.1 Full Stack Summary

| Layer | Recommended Tech |
|---|---|
| Frontend | React + TypeScript + Vite |
| Canvas | React Flow / @xyflow/react |
| Frontend state | Zustand |
| Styling | Tailwind CSS + shadcn/ui |
| Backend API | FastAPI |
| Validation | Pydantic |
| ORM / DB access | SQLAlchemy 2.0 or SQLModel |
| Main database | PostgreSQL |
| Queue / message bus | Redis Streams or Redis Queue |
| Worker | Python worker process |
| Realtime | FastAPI WebSockets |
| Trace analytics | ClickHouse |
| Local analytics optional | DuckDB |
| AI orchestration | Custom lightweight engine |
| AI providers | OpenAI and/or Anthropic |
| Auth | JWT initially; Clerk/Supabase Auth optional |
| Billing | Stripe test mode |
| Local dev | Docker Compose |
| Frontend deployment | Vercel |
| Backend deployment | Render, Fly.io, or Railway |
| Postgres deployment | Neon or Supabase |
| Redis deployment | Upstash or managed Redis |
| ClickHouse deployment | Local Docker first, ClickHouse Cloud later |

---

# 4. High-Level Architecture

```text
                ┌──────────────────────────────┐
                │          Frontend             │
                │ React + TypeScript            │
                │ React Flow Canvas             │
                │ Trace Timeline UI             │
                └───────────────┬──────────────┘
                                │
                     REST APIs + WebSocket
                                │
                ┌───────────────▼──────────────┐
                │        FastAPI Backend         │
                │ Auth, Workflow CRUD, Runs      │
                │ WebSocket Trace Gateway        │
                └───────┬──────────────┬───────┘
                        │              │
                        │              │
              ┌─────────▼──────┐ ┌─────▼─────────────┐
              │ PostgreSQL      │ │ Redis              │
              │ Users           │ │ Queue / Streams    │
              │ Workflows       │ │ Run jobs           │
              │ Workflow versions││ Live trace events  │
              │ Run metadata    │ │ Temp run state     │
              └────────────────┘ └─────┬─────────────┘
                                        │
                            ┌───────────▼───────────┐
                            │   Workflow Worker      │
                            │ Custom Engine          │
                            │ Agent Executor         │
                            │ Tool Executor          │
                            │ Router Executor        │
                            │ Retry/Fallback         │
                            │ Model Router           │
                            └───────────┬───────────┘
                                        │
                             AI calls + tool calls
                                        │
                            ┌───────────▼───────────┐
                            │      ClickHouse        │
                            │ Trace events           │
                            │ Cost analytics         │
                            │ Latency analytics      │
                            │ Replay/diff data       │
                            └───────────────────────┘
```

---

# 5. Repository Structure

Recommended monorepo:

```text
stagehand/
  PROJECT.md
  CLAUDE.md
  README.md
  .env.example
  docker-compose.yml
  Makefile

  apps/
    web/
      package.json
      vite.config.ts
      tsconfig.json
      src/
        main.tsx
        App.tsx
        routes/
        components/
        features/
          workflows/
          builder/
          runs/
          traces/
          templates/
          settings/
        lib/
        types/
        stores/

    api/
      pyproject.toml
      alembic.ini
      app/
        main.py
        config.py
        dependencies.py
        api/
          routes/
            health.py
            auth.py
            workflows.py
            runs.py
            traces.py
            evals.py
            templates.py
        core/
          security.py
          errors.py
          logging.py
        db/
          postgres.py
          clickhouse.py
          redis.py
          models/
          repositories/
          migrations/
        schemas/
        services/
          workflow_service.py
          run_service.py
          trace_service.py
          eval_service.py
        websocket/
          manager.py
          routes.py
        tests/

    worker/
      pyproject.toml
      worker/
        main.py
        config.py
        engine/
          workflow_loader.py
          workflow_validator.py
          execution_planner.py
          orchestrator.py
          context.py
          nodes/
            base.py
            input_node.py
            agent_node.py
            tool_node.py
            router_node.py
            output_node.py
          trace_emitter.py
          retry_manager.py
          model_router.py
          eval_runner.py
        ai/
          providers/
            base.py
            openai_provider.py
            anthropic_provider.py
          prompts/
        tools/
          base.py
          calculator.py
          mock_search.py
          document_search.py
          summarizer.py
        tests/

  packages/
    shared/
      schemas/
      types/

  infra/
    docker/
    deploy/
    clickhouse/
      schema.sql
    postgres/
      init.sql

  docs/
    architecture.md
    api.md
    database.md
    deployment.md
    experiments.md
```

---

# 6. CLAUDE.md Recommended Content

Create a shorter `CLAUDE.md` file in the root.

```md
# CLAUDE.md

## Project
Stagehand is a trace-first multi-agent workflow builder with live execution tracing.

## Coding Rules
- Implement one milestone at a time.
- Do not rewrite unrelated files.
- Prefer simple working code over over-engineered abstractions.
- Always add tests for backend services and worker engine logic.
- Use TypeScript types for all frontend workflow, run, and trace objects.
- Use Pydantic schemas for all backend request/response validation.
- Do not execute workflows inside API request handlers. Use worker + Redis.
- Store workflow metadata in PostgreSQL.
- Store trace events in ClickHouse.
- Use Redis for queues, streams, and live trace fanout.
- Every node execution must emit trace events.
- Never expose API keys or secrets to the frontend.
- Tool calls must use allowlists and schema validation.
- Add cost limits, max step limits, and timeouts for workflow runs.

## Current Build Order
1. Repo structure
2. Docker Compose services
3. FastAPI health endpoint
4. Postgres models
5. Workflow CRUD
6. React Flow builder
7. Redis queue
8. Worker engine
9. WebSocket live trace
10. ClickHouse trace storage
11. Replay
12. Diff
13. Evals
14. UCB model routing
15. Template gallery
16. Stripe test mode
17. Deployment
```

---

# 7. Frontend Specification

## 7.1 Frontend Responsibilities

The frontend should handle:

```text
1. Authentication screens.
2. Dashboard.
3. Workflow list.
4. Visual workflow builder.
5. Node configuration panel.
6. Run button.
7. Live trace viewer.
8. Run detail page.
9. Replay page.
10. Diff page.
11. Template gallery.
12. Settings and API key configuration.
```

## 7.2 Frontend Tech

Use:

```text
React
TypeScript
Vite
React Flow
Zustand
Tailwind CSS
shadcn/ui
Axios or Fetch
Native WebSocket client
```

## 7.3 Frontend Routes

```text
/login
/dashboard
/workflows
/workflows/:workflowId/builder
/runs/:runId
/runs/:runId/replay
/runs/:runId/diff/:otherRunId
/templates
/settings
```

## 7.4 Main Frontend Screens

### Dashboard

Shows:

```text
Total workflows
Runs today
Failed runs
Average latency
Total token cost
Most expensive workflow
Recent runs
```

### Workflow Builder

Layout:

```text
┌───────────────┬───────────────────────────────┬──────────────────────┐
│ Node Library  │        React Flow Canvas       │ Node Config Panel    │
│               │                               │                      │
│ + Input       │  Input → Agent → Tool → Output │ Prompt               │
│ + Agent       │                               │ Model policy         │
│ + Tool        │                               │ Allowed tools        │
│ + Router      │                               │ Retry count          │
│ + Output      │                               │ Cost limit           │
└───────────────┴───────────────────────────────┴──────────────────────┘
```

### Live Run Page

Shows:

```text
Run status
Current executing node
Total latency
Total cost
Total input tokens
Total output tokens
Trace timeline
Canvas node status highlighting
Detailed trace panel
```

### Replay Page

Shows:

```text
Original run
Replay run
Changed model selections
Changed tool calls
Changed outputs
Cost delta
Latency delta
Success/failure difference
```

### Diff Page

Shows:

```text
Run A vs Run B
Node-by-node comparison
Model difference
Tool difference
Token difference
Latency difference
Cost difference
Eval score difference
Error difference
```

## 7.5 Frontend Type Definitions

```ts
export type WorkflowNodeType =
  | "input"
  | "agent"
  | "tool"
  | "router"
  | "output";

export type WorkflowNodeConfig = {
  label: string;
  prompt?: string;
  modelPolicy?: "cheap" | "strong" | "adaptive";
  allowedTools?: string[];
  maxRetries?: number;
  timeoutMs?: number;
  maxCostUsd?: number;
};

export type WorkflowGraph = {
  nodes: Array<{
    id: string;
    type: WorkflowNodeType;
    position: { x: number; y: number };
    config: WorkflowNodeConfig;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    condition?: string;
  }>;
};

export type TraceEvent = {
  eventId: string;
  runId: string;
  workflowId: string;
  nodeId?: string;
  eventType:
    | "run_started"
    | "node_started"
    | "model_called"
    | "model_completed"
    | "tool_called"
    | "tool_completed"
    | "node_completed"
    | "node_failed"
    | "retry_scheduled"
    | "fallback_used"
    | "run_completed"
    | "run_failed";
  timestamp: string;
  status: "running" | "success" | "failed";
  latencyMs?: number;
  modelName?: string;
  inputTokens?: number;
  outputTokens?: number;
  estimatedCostUsd?: number;
  toolName?: string;
  retryCount?: number;
  errorMessage?: string;
  metadata?: Record<string, unknown>;
};
```

---

# 8. Backend Specification

## 8.1 Backend Responsibilities

The FastAPI backend should handle:

```text
1. Auth.
2. Workflow CRUD.
3. Workflow versioning.
4. Workflow validation.
5. Run creation.
6. Run status tracking.
7. WebSocket connections.
8. Trace retrieval.
9. Replay requests.
10. Diff requests.
11. Eval result retrieval.
12. Template APIs.
13. Usage metrics.
```

## 8.2 Backend Tech

Use:

```text
FastAPI
Pydantic
SQLAlchemy 2.0 or SQLModel
Alembic
PostgreSQL
Redis
ClickHouse client
Uvicorn
Pytest
Ruff
Mypy optional
```

## 8.3 API Endpoints

### Health

```text
GET /health
```

### Workflows

```text
POST   /workflows
GET    /workflows
GET    /workflows/{workflow_id}
PUT    /workflows/{workflow_id}
DELETE /workflows/{workflow_id}
POST   /workflows/{workflow_id}/versions
GET    /workflows/{workflow_id}/versions
```

### Runs

```text
POST /workflows/{workflow_id}/run
GET  /runs
GET  /runs/{run_id}
GET  /runs/{run_id}/trace
POST /runs/{run_id}/replay
GET  /runs/{run_id}/diff/{other_run_id}
```

### Evals

```text
POST /runs/{run_id}/eval
GET  /runs/{run_id}/eval
GET  /workflows/{workflow_id}/eval-summary
```

### Templates

```text
GET  /templates
POST /templates
GET  /templates/{template_id}
POST /templates/{template_id}/clone
```

### WebSocket

```text
WS /ws/runs/{run_id}
```

## 8.4 Backend Request/Response Schemas

### Create Workflow

```json
{
  "name": "Research Summarizer",
  "description": "Researches a topic and summarizes results",
  "graph": {
    "nodes": [],
    "edges": []
  }
}
```

### Run Workflow

```json
{
  "input": {
    "query": "Compare LangSmith and Arize Phoenix"
  },
  "run_config": {
    "max_steps": 25,
    "max_cost_usd": 0.50,
    "max_runtime_seconds": 120
  }
}
```

### Run Response

```json
{
  "run_id": "run_123",
  "workflow_id": "wf_123",
  "status": "queued",
  "created_at": "2026-06-18T00:00:00Z"
}
```

---

# 9. PostgreSQL Database Design

Use PostgreSQL for transactional product data.

## 9.1 Tables

### users

```text
id UUID primary key
email text unique not null
name text
created_at timestamptz
updated_at timestamptz
```

### organizations

```text
id UUID primary key
name text not null
created_at timestamptz
updated_at timestamptz
```

### projects

```text
id UUID primary key
organization_id UUID
name text not null
created_at timestamptz
updated_at timestamptz
```

### workflows

```text
id UUID primary key
project_id UUID
owner_user_id UUID
name text not null
description text
current_version_id UUID
created_at timestamptz
updated_at timestamptz
```

### workflow_versions

```text
id UUID primary key
workflow_id UUID
version_number integer
graph_json jsonb not null
created_at timestamptz
created_by_user_id UUID
```

### workflow_runs

```text
id UUID primary key
workflow_id UUID
workflow_version_id UUID
status text
input_json jsonb
output_json jsonb
error_message text
total_latency_ms integer
total_input_tokens integer
total_output_tokens integer
estimated_cost_usd numeric
started_at timestamptz
completed_at timestamptz
created_at timestamptz
```

### eval_results

```text
id UUID primary key
run_id UUID
success_score numeric
tool_correctness_score numeric
format_score numeric
quality_score numeric
cost_score numeric
latency_score numeric
metadata_json jsonb
created_at timestamptz
```

### templates

```text
id UUID primary key
name text
description text
graph_json jsonb
is_public boolean
created_by_user_id UUID
created_at timestamptz
```

### api_keys

```text
id UUID primary key
user_id UUID
provider text
encrypted_key text
created_at timestamptz
```

## 9.2 Why PostgreSQL

Use PostgreSQL because:

```text
1. Workflow definitions need reliable transactional storage.
2. Users, organizations, projects, and permissions are relational data.
3. Workflow versions need consistency.
4. JSONB is useful for storing graph definitions.
5. It is widely used in production systems.
```

---

# 10. ClickHouse Trace Design

Use ClickHouse for append-heavy trace analytics.

## 10.1 Main Table: trace_events

```sql
CREATE TABLE IF NOT EXISTS trace_events (
    event_id UUID,
    run_id UUID,
    workflow_id UUID,
    workflow_version_id UUID,
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
```

## 10.2 Event Types

```text
run_started
node_started
model_called
model_completed
tool_called
tool_completed
tool_failed
node_completed
node_failed
retry_scheduled
fallback_used
eval_started
eval_completed
run_completed
run_failed
```

## 10.3 Analytics Queries

Examples:

```sql
SELECT
  node_id,
  avg(latency_ms) AS avg_latency
FROM trace_events
WHERE workflow_id = {workflow_id:String}
GROUP BY node_id
ORDER BY avg_latency DESC;
```

```sql
SELECT
  model_name,
  sum(estimated_cost_usd) AS total_cost,
  sum(input_tokens + output_tokens) AS total_tokens
FROM trace_events
WHERE workflow_id = {workflow_id:String}
GROUP BY model_name
ORDER BY total_cost DESC;
```

```sql
SELECT
  event_type,
  count() AS count
FROM trace_events
WHERE run_id = {run_id:String}
GROUP BY event_type;
```

## 10.4 Why ClickHouse

Use ClickHouse because trace data is:

```text
append-heavy
time-series-like
analytical
rarely updated
queried by workflow, run, model, node, latency, cost, and status
```

---

# 11. Redis Design

Use Redis for:

```text
1. Workflow run queue.
2. Worker job dispatch.
3. Trace event stream.
4. WebSocket fanout.
5. Temporary run state.
```

## 11.1 Redis Keys

```text
queue:workflow_runs
run:{run_id}:status
run:{run_id}:events
run:{run_id}:locks
```

## 11.2 Redis Event Example

```json
{
  "event_id": "evt_123",
  "run_id": "run_123",
  "workflow_id": "wf_123",
  "node_id": "agent_1",
  "event_type": "node_started",
  "timestamp": "2026-06-18T00:00:00Z",
  "status": "running"
}
```

## 11.3 Why Redis

Use Redis because:

```text
1. Workflow execution should not block API requests.
2. Workers need a simple queue.
3. WebSockets need live event fanout.
4. Temporary run state should be fast.
5. Redis is simpler than Kafka for MVP.
```

Kafka can be a future migration if the system needs high-throughput durable event streaming across many consumers.

---

# 12. Custom Orchestration Engine

## 12.1 Purpose

The custom orchestration engine executes workflow graphs and emits structured trace events for every step.

This engine is not meant to replace LangGraph completely. It is a lightweight trace-first engine designed for this portfolio project.

## 12.2 Engine Components

```text
WorkflowLoader
WorkflowValidator
ExecutionPlanner
ExecutionContext
Orchestrator
NodeExecutor
InputNodeExecutor
AgentNodeExecutor
ToolNodeExecutor
RouterNodeExecutor
OutputNodeExecutor
TraceEmitter
RetryManager
ModelRouter
EvalRunner
```

## 12.3 Engine Flow

```text
1. Worker receives run_id.
2. Load run metadata from PostgreSQL.
3. Load workflow version graph from PostgreSQL.
4. Validate graph.
5. Create execution context.
6. Emit run_started.
7. Execute nodes according to graph order and conditions.
8. For each node:
   - emit node_started
   - prepare input
   - execute node
   - emit model/tool events if needed
   - apply retry/fallback if needed
   - store output in context
   - emit node_completed or node_failed
9. Emit run_completed or run_failed.
10. Store trace events in ClickHouse.
11. Update run status in PostgreSQL.
```

## 12.4 Node Types

### Input Node

Accepts workflow input.

### Agent Node

Calls an AI model.

Config:

```json
{
  "prompt": "You are a research agent.",
  "model_policy": "adaptive",
  "temperature": 0.2,
  "max_tokens": 1000,
  "allowed_tools": ["mock_search", "summarizer"],
  "max_retries": 2,
  "fallback_model": "strong"
}
```

### Tool Node

Calls a predefined safe tool.

MVP tools:

```text
calculator
mock_search
document_search
summarizer
```

### Router Node

Chooses the next edge based on model output or rule condition.

### Output Node

Returns final workflow output.

## 12.5 Execution Safety Limits

Every run must enforce:

```text
max_steps_per_run
max_runtime_seconds
max_cost_usd
max_tokens_per_run
max_retries_per_node
timeout_per_model_call
timeout_per_tool_call
allowed_tools_per_agent
```

---

# 13. AI Models and AI Design

## 13.1 Model Strategy

Use two classes of models:

```text
Cheap model:
- routing
- classification
- simple extraction
- simple summarization

Strong model:
- complex reasoning
- final synthesis
- eval judging
- fallback when cheap model fails
```

## 13.2 Provider Abstraction

Do not hard-code only one provider.

Create an interface:

```python
class ModelProvider:
    async def generate(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> ModelResponse:
        ...
```

## 13.3 Model Response

```python
class ModelResponse(BaseModel):
    text: str
    model_name: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    latency_ms: int
    raw_response: dict | None = None
```

## 13.4 Initial Models

Start with one provider to save complexity.

Example model setup:

```text
cheap_model = "small/mini/haiku-style model"
strong_model = "sonnet/gpt-4-class model"
```

Store actual model names in environment variables:

```env
CHEAP_MODEL_NAME=
STRONG_MODEL_NAME=
DEFAULT_EVAL_MODEL_NAME=
```

## 13.5 Where AI Is Used

```text
Agent nodes
Router nodes
Tool selection
Final synthesis
LLM-as-judge eval
Adaptive model routing
```

---

# 14. Tool Calling Design

## 14.1 Tool Requirements

Every tool must have:

```text
name
description
input schema
output schema
timeout
safe/unsafe classification
executor function
```

## 14.2 Tool Interface

```python
class Tool(BaseModel):
    name: str
    description: str

    async def execute(self, input_data: dict) -> dict:
        ...
```

## 14.3 MVP Tools

### Calculator

Useful for deterministic testing.

### Mock Search

Returns predefined search results from local data.

### Document Search

Searches local documents or seeded content.

### Summarizer

Summarizes text using model or deterministic logic.

## 14.4 Tool Security

```text
No arbitrary shell execution.
No unrestricted web browsing in MVP.
No raw API key exposure.
Every tool input must be validated.
Every tool call must be logged.
Every tool call must emit trace events.
```

---

# 15. Retry and Fallback

## 15.1 Retry Conditions

Retry on:

```text
timeout
rate limit
temporary provider error
invalid JSON
empty response
tool transient failure
```

Do not retry:

```text
permission denied
invalid tool
cost limit exceeded
max steps exceeded
unsafe tool call
```

## 15.2 Retry Strategy

```text
max_retries = 2
backoff = exponential
jitter = small random delay
```

## 15.3 Fallback Strategy

Use fallback when:

```text
cheap model fails validation
cheap model output fails eval
tool call repeatedly fails
node exceeds retries
```

Example:

```text
cheap model attempt 1 -> invalid JSON
cheap model attempt 2 -> invalid JSON
strong model fallback -> valid JSON
```

Every retry/fallback must emit trace events.

---

# 16. Eval Harness

## 16.1 Purpose

The eval harness determines whether a workflow completed a task correctly.

## 16.2 Eval Types

```text
Exact match eval
JSON schema eval
Tool usage eval
Latency eval
Cost eval
LLM-as-judge eval
```

## 16.3 Eval Result Schema

```json
{
  "run_id": "run_123",
  "success_score": 0.87,
  "tool_correctness_score": 1.0,
  "format_score": 1.0,
  "quality_score": 0.85,
  "cost_score": 0.78,
  "latency_score": 0.74,
  "metadata": {}
}
```

## 16.4 Benchmark Set

Create benchmark workflows:

```text
1. Simple routing task.
2. Research and summarize task.
3. Tool-required task.
4. Multi-step synthesis task.
5. Failure/retry task.
6. Cost-sensitive routing task.
```

Each benchmark should include:

```text
input
expected behavior
required tools
expected output schema
success criteria
```

---

# 17. UCB Bandit Model Router

## 17.1 Purpose

The UCB bandit chooses between cheap and strong models for each node/task type to reduce cost while preserving quality.

## 17.2 Build Order

Only build UCB after:

```text
tracing works
replay works
eval harness works
benchmark suite exists
```

## 17.3 Formula

```text
UCB(model) = average_reward(model) + c * sqrt(log(total_trials) / trials_for_model)
```

## 17.4 Reward Function

Use:

```text
reward = 0.7 * quality_score + 0.2 * latency_score + 0.1 * cost_score
```

Alternative:

```text
reward = task_success - lambda * normalized_cost - beta * normalized_latency
```

## 17.5 Metrics

Track:

```text
model_name
node_type
task_type
trials
average_reward
average_cost
average_latency
success_rate
fallback_rate
```

## 17.6 Experiment

Compare:

```text
Baseline:
All nodes use strong model.

Experiment:
Router chooses cheap or strong model using UCB.

Measure:
average cost per run
success rate
average latency
quality score
fallback rate
```

Only claim a cost reduction after real benchmark results.

---

# 18. Replay and Diff

## 18.1 Replay

Replay means rerunning the same workflow version with the same input.

Store:

```text
original_run_id
replay_run_id
workflow_version_id
same_input
same_config
timestamp
```

Replay should answer:

```text
Did failure happen again?
Did fallback fix it?
Did model selection change?
Did cost change?
Did latency change?
```

## 18.2 Diff

Diff compares two runs.

Compare:

```text
node status
model used
tool used
node output
latency
tokens
cost
retry count
fallback usage
error message
eval score
```

Diff output example:

```json
{
  "run_a": "run_success",
  "run_b": "run_failed",
  "differences": [
    {
      "node_id": "router_1",
      "field": "model_name",
      "run_a_value": "strong_model",
      "run_b_value": "cheap_model"
    },
    {
      "node_id": "tool_1",
      "field": "status",
      "run_a_value": "success",
      "run_b_value": "failed"
    }
  ]
}
```

---

# 19. Security Requirements

## 19.1 Application Security

```text
Use authentication.
Check workflow ownership on every request.
Never expose secrets to frontend.
Encrypt stored provider API keys.
Rate-limit workflow runs.
Validate all request bodies with Pydantic.
Use CORS carefully.
Use HTTPS in deployment.
```

## 19.2 Agent Security

```text
Tool allowlists per agent.
Strict tool input schemas.
Max steps per run.
Max runtime per run.
Max cost per run.
Max tokens per run.
Timeout per model call.
Timeout per tool call.
No arbitrary code execution.
Audit every tool call.
```

## 19.3 Prompt Injection Protection

MVP protections:

```text
Do not let model output modify tool permissions.
Do not let model output reveal secrets.
Do not send API keys to models.
Keep system prompts server-side.
Validate tool names against allowlist.
Validate tool arguments with schemas.
```

---

# 20. Cost Management

## 20.1 Cost Controls

```text
Use cheap model for routing/simple tasks.
Use strong model only for synthesis/evals/fallback.
Cache repeated prompts where possible.
Set provider spend limits.
Add app-level max_cost_usd per run.
Limit demo users to a few runs.
Use mock tools for testing.
Run benchmark suite with small inputs.
```

## 20.2 Expected Build Cost

```text
Local development:
$10-$50/month mostly for LLM API usage.

Hosted MVP:
$20-$80/month.

Polished demo:
$50-$150/month.

Production-like:
$200+/month.
```

Most infrastructure can start free or local:

```text
Vercel free
Neon/Supabase free
Upstash free
ClickHouse local Docker
Stripe test mode free
```

---

# 21. Local Development Setup

## 21.1 Required Tools

```text
Node.js 20+
Python 3.11+
Docker
Docker Compose
PostgreSQL client optional
Redis CLI optional
Git
Claude Code
```

## 21.2 Environment Variables

Create `.env.example`:

```env
# App
APP_ENV=development
API_PORT=8000
FRONTEND_URL=http://localhost:5173

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=stagehand
POSTGRES_USER=stagehand
POSTGRES_PASSWORD=stagehand

# Redis
REDIS_URL=redis://localhost:6379/0

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DATABASE=stagehand

# Auth
JWT_SECRET=replace_me
JWT_EXPIRES_MINUTES=1440

# AI Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
CHEAP_MODEL_NAME=
STRONG_MODEL_NAME=
DEFAULT_EVAL_MODEL_NAME=

# Cost Limits
DEFAULT_MAX_COST_USD=0.50
DEFAULT_MAX_STEPS=25
DEFAULT_MAX_RUNTIME_SECONDS=120

# Stripe optional
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

## 21.3 Docker Compose Services

```text
postgres
redis
clickhouse
api
worker
web
```

Start local services:

```bash
docker compose up -d postgres redis clickhouse
```

Run API:

```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```

Run worker:

```bash
cd apps/worker
python -m worker.main
```

Run frontend:

```bash
cd apps/web
npm install
npm run dev
```

---

# 22. Step-by-Step Build Plan

## Milestone 0: Planning and Repo Setup

Tasks:

```text
1. Create monorepo structure.
2. Add PROJECT.md.
3. Add CLAUDE.md.
4. Add README.md.
5. Add .env.example.
6. Add docker-compose.yml with Postgres, Redis, ClickHouse.
7. Add Makefile commands.
```

Acceptance criteria:

```text
Repo structure exists.
Docker services start.
README explains how to run locally.
```

## Milestone 1: Backend Foundation

Tasks:

```text
1. Create FastAPI app.
2. Add config loading.
3. Add health endpoint.
4. Add Postgres connection.
5. Add Alembic migrations.
6. Add base models.
7. Add basic tests.
```

Acceptance criteria:

```text
GET /health returns OK.
Postgres connects.
Migrations run.
Tests pass.
```

## Milestone 2: Workflow CRUD

Tasks:

```text
1. Add workflow models.
2. Add workflow_versions model.
3. Add Pydantic schemas.
4. Add create workflow endpoint.
5. Add list workflows endpoint.
6. Add get workflow endpoint.
7. Add update workflow endpoint.
8. Add graph validation.
```

Acceptance criteria:

```text
User can save workflow graph.
User can load workflow graph.
Invalid graph is rejected.
```

## Milestone 3: Frontend Foundation

Tasks:

```text
1. Create Vite React TypeScript app.
2. Add Tailwind.
3. Add shadcn/ui.
4. Add routing.
5. Add dashboard layout.
6. Add API client.
7. Add global state with Zustand.
```

Acceptance criteria:

```text
Frontend runs.
Dashboard renders.
API health check works from UI.
```

## Milestone 4: React Flow Builder

Tasks:

```text
1. Add React Flow canvas.
2. Add node sidebar.
3. Add custom node components.
4. Add drag/drop node creation.
5. Add edge connection.
6. Add node config panel.
7. Add save/load workflow.
```

Acceptance criteria:

```text
User can build workflow visually.
User can save workflow.
User can reload saved workflow.
```

## Milestone 5: Redis Queue and Run Creation

Tasks:

```text
1. Add workflow_runs table.
2. Add POST /workflows/{id}/run.
3. Create run record.
4. Push run job to Redis.
5. Return run_id.
```

Acceptance criteria:

```text
Clicking run creates queued run.
Run job appears in Redis.
```

## Milestone 6: Worker Service and Basic Engine

Tasks:

```text
1. Create worker process.
2. Poll Redis for run jobs.
3. Load workflow version.
4. Implement WorkflowValidator.
5. Implement ExecutionContext.
6. Implement simple topological execution.
7. Support input and output nodes first.
8. Update run status.
```

Acceptance criteria:

```text
Worker picks job.
Workflow run changes from queued to running to completed.
Output is stored.
```

## Milestone 7: Trace Event Pipeline

Tasks:

```text
1. Define TraceEvent schema.
2. Implement TraceEmitter.
3. Emit run_started.
4. Emit node_started.
5. Emit node_completed.
6. Emit run_completed.
7. Publish trace events to Redis.
8. Store trace events in ClickHouse.
```

Acceptance criteria:

```text
Every run produces trace events.
Trace events exist in ClickHouse.
Trace events can be fetched through API.
```

## Milestone 8: WebSocket Live Tracing

Tasks:

```text
1. Add WebSocket endpoint /ws/runs/{run_id}.
2. Subscribe to Redis run events.
3. Push trace events to connected clients.
4. Build frontend live timeline.
5. Highlight active node on canvas.
```

Acceptance criteria:

```text
User sees run events live while workflow executes.
Canvas updates node status.
```

## Milestone 9: Agent and Tool Nodes

Tasks:

```text
1. Add ModelProvider abstraction.
2. Add cheap/strong model config.
3. Implement AgentNodeExecutor.
4. Implement ToolNodeExecutor.
5. Add calculator tool.
6. Add mock_search tool.
7. Add model_called/model_completed events.
8. Add tool_called/tool_completed events.
```

Acceptance criteria:

```text
Agent node can call model.
Tool node can call safe tools.
Trace shows model and tool details.
```

## Milestone 10: Retry and Fallback

Tasks:

```text
1. Implement RetryManager.
2. Add retry config per node.
3. Add timeout handling.
4. Add fallback model.
5. Emit retry_scheduled.
6. Emit fallback_used.
7. Show retry/fallback in UI.
```

Acceptance criteria:

```text
Failed model/tool calls retry.
Fallback model is used when configured.
Trace shows retry and fallback events.
```

## Milestone 11: Run Detail Page

Tasks:

```text
1. Build /runs/:runId page.
2. Fetch run metadata.
3. Fetch trace events.
4. Show timeline.
5. Show metrics summary.
6. Show node detail panel.
```

Acceptance criteria:

```text
Completed run can be inspected after execution.
User can see cost, tokens, latency, status, model, tools.
```

## Milestone 12: Replay

Tasks:

```text
1. Add POST /runs/{run_id}/replay.
2. Create new run from original workflow version and input.
3. Link original_run_id to replay_run_id.
4. Build replay UI.
```

Acceptance criteria:

```text
User can replay a previous run.
Replay result is linked to original.
```

## Milestone 13: Diff

Tasks:

```text
1. Add diff service.
2. Compare two runs by node_id.
3. Compare status/model/tool/tokens/cost/latency/output/error.
4. Add GET /runs/{run_id}/diff/{other_run_id}.
5. Build diff UI.
```

Acceptance criteria:

```text
User can compare two runs.
UI shows meaningful node-by-node differences.
```

## Milestone 14: Eval Harness

Tasks:

```text
1. Add eval_results table.
2. Implement exact match eval.
3. Implement JSON schema eval.
4. Implement tool usage eval.
5. Implement LLM-as-judge eval.
6. Add POST /runs/{run_id}/eval.
7. Show eval result in UI.
```

Acceptance criteria:

```text
Run receives success score.
Eval results are visible.
```

## Milestone 15: UCB Model Router

Tasks:

```text
1. Create model_routing_stats table.
2. Implement reward function.
3. Implement UCB formula.
4. Route agent nodes adaptively.
5. Store routing decisions.
6. Compare baseline vs adaptive.
7. Show model routing dashboard.
```

Acceptance criteria:

```text
Adaptive router chooses cheap/strong models.
Routing decisions are traced.
Cost/quality metrics are measurable.
```

## Milestone 16: Template Gallery

Tasks:

```text
1. Add templates table.
2. Seed sample templates.
3. Build template gallery.
4. Add clone template to workflow.
5. Add shareable workflow URLs.
```

Acceptance criteria:

```text
User can create workflow from template.
User can share workflow URL.
```

## Milestone 17: Stripe Test Mode

Tasks:

```text
1. Create usage_events table.
2. Track runs and token usage.
3. Add usage dashboard.
4. Add Stripe test customer.
5. Add Stripe checkout/test billing portal optional.
6. Do not charge real money.
```

Acceptance criteria:

```text
Usage dashboard works.
Stripe test mode integration works.
No real payments required.
```

## Milestone 18: Deployment

Tasks:

```text
1. Deploy frontend to Vercel.
2. Deploy API to Render/Fly/Railway.
3. Deploy worker to same platform.
4. Use Neon/Supabase Postgres.
5. Use Upstash Redis.
6. Use ClickHouse Cloud or hosted ClickHouse.
7. Configure environment variables.
8. Run migrations.
9. Test live run.
10. Add demo workflow.
```

Acceptance criteria:

```text
Public frontend URL works.
Backend health endpoint works.
User can create workflow.
User can run workflow.
Live trace works.
Run detail works.
Replay and diff work.
```

---

# 23. Testing Plan

## 23.1 Backend Tests

Test:

```text
workflow creation
workflow validation
workflow versioning
run creation
trace retrieval
replay creation
diff service
eval service
auth checks
```

## 23.2 Worker Tests

Test:

```text
graph validation
topological execution
node execution
trace emission
retry handling
fallback handling
tool validation
model provider mocks
cost limit enforcement
max step enforcement
```

## 23.3 Frontend Tests

Test:

```text
workflow builder renders
node creation works
edge creation works
node config updates
save workflow works
live trace timeline renders
run detail renders
diff page renders
```

## 23.4 Integration Tests

Test:

```text
create workflow -> run workflow -> worker executes -> traces stored -> UI displays traces
```

---

# 24. Deployment Plan

## 24.1 Local Docker

Use Docker Compose for:

```text
postgres
redis
clickhouse
```

Keep API, worker, frontend local during development.

## 24.2 Hosted Portfolio Deployment

Recommended:

```text
Frontend: Vercel
Backend API: Render or Fly.io
Worker: Render or Fly.io background worker
Postgres: Neon
Redis: Upstash
ClickHouse: ClickHouse Cloud trial/small instance
Domain: optional
```

## 24.3 Deployment Checklist

```text
Environment variables configured.
CORS allows frontend domain.
Database migrations applied.
ClickHouse schema applied.
Redis connection works.
WebSocket connection works.
Worker is running.
LLM API key works.
Demo account exists.
Demo workflow exists.
Spend limits enabled.
Public demo run limit enabled.
```

---

# 25. Resume Bullets

Use only after building.

## Core Resume Bullet

```text
Built Stagehand, a full-stack multi-agent workflow builder with a React Flow canvas, FastAPI orchestration engine, Redis-backed async execution, WebSocket live tracing, PostgreSQL workflow versioning, and ClickHouse trace analytics, enabling users to design, run, replay, and debug AI workflows with per-step latency, token cost, model decisions, tool calls, retries, and failures.
```

## Advanced Resume Bullet

```text
Implemented an eval-driven adaptive model router using a UCB bandit across cheap and strong models, reducing average token cost across benchmark workflows while preserving task success and output quality.
```

## Only Use If Measured

```text
Reduced average token cost by 31% across 60 benchmark runs while keeping workflow success within 3% of the strong-model baseline.
```

---

# 26. Interview Defense

## Why did you build this?

Multi-agent workflows are hard to debug. Developers need to see why agents select tools, where failures occur, where latency and cost increase, and whether the workflow completed the task correctly. Stagehand makes these workflows observable, replayable, and cost-aware.

## Why React Flow?

The product needs a node-based visual workflow editor. React Flow gives draggable nodes, edges, zoom/pan, custom nodes, and graph state without building a canvas engine from scratch.

## Why FastAPI?

The backend is AI-heavy and Python fits LLM tooling well. FastAPI provides async APIs, Pydantic validation, WebSocket support, and clean OpenAPI docs.

## Why Redis?

Workflow runs should not block API requests. Redis provides a simple queue and live event stream for workers and WebSocket fanout.

## Why PostgreSQL?

PostgreSQL is used for transactional data: users, workflows, workflow versions, runs, templates, and settings.

## Why ClickHouse?

Trace events are append-heavy analytical data. ClickHouse is better for aggregating cost, latency, tokens, failures, and model usage.

## Why not Kafka?

Kafka is powerful but operationally heavier. Redis Streams is enough for the MVP. Kafka would be considered if the system needed higher event throughput, durable multi-consumer streams, and long retention.

## Why custom orchestration engine?

The goal is trace-first execution. A small custom engine gives full control over node execution, retries, fallback, model routing, and trace emission. It is not meant to replace LangGraph; it is built to expose execution internals clearly.

## How do you secure it?

Use auth, ownership checks, tool allowlists, Pydantic validation, encrypted API keys, cost limits, rate limits, max-step limits, timeouts, audit logs, and no arbitrary code execution.

## How does it scale?

API, worker, Redis, Postgres, and ClickHouse are separated. API servers and workers can scale independently. Workers scale based on queue depth. ClickHouse handles analytical trace queries. Postgres stays focused on transactional data.

---

# 27. Final Build Order Summary

```text
1. Repo setup
2. Docker services
3. FastAPI foundation
4. Postgres schema
5. Workflow CRUD
6. React Flow builder
7. Redis queue
8. Worker service
9. Custom orchestration engine
10. Trace event pipeline
11. WebSocket live tracing
12. ClickHouse trace storage
13. Agent and tool nodes
14. Retry and fallback
15. Run detail page
16. Replay
17. Diff
18. Eval harness
19. UCB model router
20. Template gallery
21. Stripe test mode
22. Deployment
23. Benchmark report
24. Final README and resume bullets
```

---

# 28. Final Definition

Stagehand is a full-stack, trace-first multi-agent workflow platform that lets users visually design AI workflows, execute them asynchronously, stream every execution event live, store traces for analytics, replay failures, compare runs, evaluate workflow quality, and reduce token cost through adaptive model routing.

The project is strong because it combines:

```text
AI agents
full-stack development
backend systems
real-time WebSockets
databases
async workers
observability
evals
cost optimization
security
deployment
SaaS product thinking
```

Build it in phases. Do not try to build everything in one Claude Code prompt. The correct approach is milestone-by-milestone implementation with tests after each milestone.
