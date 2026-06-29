# Deployment

Stagehand is **local-first**: everything runs on your machine with Docker Compose
(Postgres, Redis, ClickHouse) plus the API, worker, and frontend on the host. This
document covers taking that same code to a managed cloud deployment without
changing how local development works.

No secrets live in this repo. Every cloud secret is set in the provider dashboard.

---

## A. Architecture

```text
                    ┌─────────────────────────┐
                    │   Browser (user)         │
                    └────────────┬─────────────┘
                                 │ HTTPS + WSS
                                 ▼
        ┌────────────────────────────────────────────┐
        │  Vercel — Frontend (Vite/React static SPA)   │
        │  VITE_API_BASE_URL / VITE_WS_BASE_URL        │
        └───────────────┬──────────────────────────────┘
                        │ HTTPS (REST) + WSS (live traces)
                        ▼
        ┌────────────────────────────────────────────┐
        │  Render — stagehand-api (FastAPI / uvicorn)  │
        │  /health, /workflows, /runs, /ws/runs/...    │
        └───┬───────────────┬───────────────┬──────────┘
            │ enqueue runs   │ SQL           │ trace reads
            ▼                ▼               ▼
   ┌─────────────┐   ┌──────────────┐  ┌──────────────────┐
   │ Upstash     │   │ Neon/Supabase│  │ ClickHouse Cloud │
   │ Redis       │   │ PostgreSQL   │  │ (trace_events)   │
   └──────┬──────┘   └──────▲───────┘  └─────────▲────────┘
          │ consume runs    │ SQL                │ trace writes
          ▼                 │                    │
   ┌──────────────────────────────────────────────────────┐
   │  Render — stagehand-worker (engine + run consumer)     │
   └──────────────────────────────────────────────────────┘
```

- **Vercel** → frontend (static build)
- **Render** → API (web service) + worker (background service)
- **Neon / Supabase** → PostgreSQL (product/transactional data)
- **Upstash** → Redis (run queue + WebSocket trace fanout)
- **ClickHouse Cloud** → trace events / analytics

Render is the reference platform; **Railway and Fly.io work the same way** — see
[§G](#g-railway--flyio-notes). The same Dockerfiles and env vars apply everywhere.

---

## B. Required accounts

- **GitHub** — source repo
- **Vercel** — frontend hosting
- **Render** (or Railway / Fly.io) — API + worker hosting
- **Neon** (or Supabase) — managed PostgreSQL
- **Upstash** — managed Redis
- **ClickHouse Cloud** — managed ClickHouse (a hosted Docker instance also works)

---

## C. Step-by-step deployment

### 1. Push the repo to GitHub
```bash
git push origin main
```

### 2. Create the PostgreSQL database (Neon/Supabase)
- Create a project and copy the connection string.
- Stagehand accepts `postgres://`, `postgresql://`, or `postgresql+psycopg2://` —
  the scheme is normalized automatically. This becomes `DATABASE_URL`.

### 3. Create the Redis database (Upstash)
- Create a Redis database, enable TLS, and copy the `rediss://` URL → `REDIS_URL`.

### 4. Create the ClickHouse database (ClickHouse Cloud)
- Create a service, then note host, port (**8443**, TLS), user, and password.
- Set `CLICKHOUSE_SECURE=true` and `CLICKHOUSE_PORT=8443` for Cloud.
- The `trace_events` table is created automatically by the worker on first write
  (`ensure_trace_table`); no manual schema step is required. You may also apply
  `infra/clickhouse/schema.sql` ahead of time.

### 5. Deploy the API service
**Option A — Blueprint (recommended):** in Render, **New → Blueprint** and point at
this repo. `render.yaml` defines `stagehand-api` and `stagehand-worker`. Fill in the
`sync: false` secrets in the dashboard.

**Option B — Manual web service:**
- Environment: **Docker**
- Dockerfile path: `apps/api/Dockerfile`, Docker context: `apps/api`
- Health check path: `/health`
- Pre-deploy command: `alembic upgrade head`
- Start command: provided by the Dockerfile (`uvicorn app.main:app --port $PORT`)
- Add the API env vars from [§D](#d-required-environment-variables).

### 6. Run migrations
- With the Blueprint, the API's **pre-deploy command** (`alembic upgrade head`) runs
  automatically on every deploy.
- Manually (any host) you can run [`scripts/deploy_api.sh`](../scripts/deploy_api.sh),
  which installs deps, runs `alembic upgrade head`, then starts uvicorn.

### 7. Deploy the worker service
- Render: type **Background Worker**, Docker, Dockerfile `apps/worker/Dockerfile`,
  context `apps/worker`. No health check / port (it has no HTTP server).
- Start the worker **only after** migrations are applied (step 6). The worker never
  runs migrations itself. See [`scripts/start_worker.sh`](../scripts/start_worker.sh).

### 8. Deploy the frontend (Vercel)
- **New Project → Import** this repo.
- **Root Directory:** `apps/web`
- Framework: **Vite** · Build command: `npm run build` · Output: `dist`
- (`apps/web/vercel.json` already encodes this, including the SPA rewrite so deep
  links like `/runs/:runId` resolve to `index.html`.)
- Set the frontend env vars from [§D](#d-required-environment-variables).

### 9. Configure CORS and frontend env
- Set the API's `FRONTEND_URL` to the Vercel URL (e.g. `https://stagehand.vercel.app`).
  Add any extra origins to `BACKEND_CORS_ORIGINS` (comma-separated). `localhost:5173`
  and `localhost:5174` are always allowed.
- Set the frontend's `VITE_API_BASE_URL` to the API URL (e.g.
  `https://stagehand-api.onrender.com`). `VITE_WS_BASE_URL` is optional — when
  omitted, the WS URL is derived from the API URL (`https` → `wss`). Redeploy the
  frontend after changing `VITE_*` (they are baked in at build time).

### 10. Smoke test
Run the checklist in [§E](#e-smoke-test-checklist).

---

## D. Required environment variables

### API (`stagehand-api`)
| Variable | Required | Notes |
|---|---|---|
| `APP_ENV` | no | `production` |
| `FRONTEND_URL` | yes | Vercel URL; added to CORS allow-list |
| `BACKEND_CORS_ORIGINS` | no | Extra origins, comma-separated |
| `DATABASE_URL` | yes | Neon/Supabase connection string |
| `REDIS_URL` | yes | Upstash `rediss://` URL |
| `CLICKHOUSE_HOST` | yes | ClickHouse Cloud host |
| `CLICKHOUSE_PORT` | yes | `8443` for Cloud |
| `CLICKHOUSE_USER` | yes | |
| `CLICKHOUSE_PASSWORD` | yes | |
| `CLICKHOUSE_DATABASE` | yes | e.g. `stagehand` |
| `CLICKHOUSE_SECURE` | yes | `true` for Cloud |
| `OPENAI_API_KEY` | no | optional; mock provider used if absent |
| `ANTHROPIC_API_KEY` | no | optional |
| `CHEAP_MODEL_NAME` | no | |
| `STRONG_MODEL_NAME` | no | |
| `DEFAULT_EVAL_MODEL_NAME` | no | |
| `BILLING_MODE` | no | `mock` (default) or `stripe_test` |
| `STRIPE_SECRET_KEY` | no | test key only (`sk_test_...`) |
| `STRIPE_WEBHOOK_SECRET` | no | |
| `STRIPE_PRICE_ID` | no | |

### Worker (`stagehand-worker`)
Same data-plane and AI variables as the API: `DATABASE_URL`, `REDIS_URL`, all
`CLICKHOUSE_*`, the AI model vars, plus `UCB_EXPLORATION_WEIGHT` (default `1.0`) and
`BILLING_MODE`. The worker has **no** CORS/`FRONTEND_URL`/Stripe vars.

### Frontend (Vercel)
| Variable | Required | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | yes | API base URL, e.g. `https://stagehand-api.onrender.com` |
| `VITE_WS_BASE_URL` | no | Defaults to API URL with `wss://` |

---

## E. Smoke test checklist

- [ ] `GET /health` → `{"status":"ok"}`
- [ ] `GET /health/db` → `{"status":"ok","database":"connected"}`
- [ ] `GET /health/redis` → `{"status":"ok","redis":"connected"}`
- [ ] `GET /health/clickhouse` → `{"status":"ok","clickhouse":"connected"}`
- [ ] Frontend loads (no console CORS errors)
- [ ] Template gallery loads
- [ ] Clone a template into a workflow
- [ ] Run the workflow (run is created and enqueued)
- [ ] Live trace streams over WebSocket while the run executes
- [ ] Run detail page shows tokens / cost / latency / model / tool / retries
- [ ] Eval runs and stores a result
- [ ] Usage dashboard loads

---

## F. Troubleshooting

- **CORS error in browser console** — `FRONTEND_URL` (or `BACKEND_CORS_ORIGINS`) on
  the API does not match the exact Vercel origin (scheme + host, no trailing slash).
  Fix the value and redeploy the API.
- **WebSocket fails to connect** — the API base is `https` but the WS URL resolved to
  `ws://` (mixed content blocked). Ensure `VITE_API_BASE_URL` uses `https://` so it
  derives `wss://`, or set `VITE_WS_BASE_URL` explicitly. Confirm the host allows
  WebSocket upgrades.
- **Runs stay `queued` / Redis queue not consumed** — the worker isn't running or
  points at a different `REDIS_URL` than the API. Check worker logs and confirm both
  services share the same Redis URL.
- **ClickHouse connection issue** — for Cloud you must set `CLICKHOUSE_SECURE=true`
  and `CLICKHOUSE_PORT=8443`. A plaintext connection to a TLS port hangs or errors.
- **Migration failure** — run `alembic upgrade head` manually against `DATABASE_URL`
  and read the error. Ensure the DB user can create tables and the URL is reachable.
- **Frontend points at the wrong backend** — `VITE_*` vars are baked in at build
  time; changing them requires a redeploy of the frontend.
- **Worker stale / not running** — restart the worker service; verify it starts only
  after migrations have created the tables it queries.

---

## G. Railway / Fly.io notes

The Dockerfiles and env vars are platform-agnostic.

- **Railway** — create two services from this repo. For the API, set the Dockerfile to
  `apps/api/Dockerfile` (root `apps/api`) and a deploy/pre-start command of
  `alembic upgrade head`; Railway injects `PORT`. For the worker, use
  `apps/worker/Dockerfile`. Add the same env vars as in [§D](#d-required-environment-variables).
- **Fly.io** — `fly launch` per app using its Dockerfile. Bind the API to
  `0.0.0.0:$PORT` (the Dockerfile already does), set the health check to `/health`,
  and run `alembic upgrade head` as a release command. Run the worker as a separate
  app/process with no public service.

---

## Local development (unchanged)

```bash
make up                              # Postgres + Redis + ClickHouse via Docker
cd apps/api && source .venv/bin/activate && alembic upgrade head && \
  uvicorn app.main:app --reload --port 8000
cd apps/worker && source .venv/bin/activate && python -m worker.main
cd apps/web && npm run dev
```

Locally, leave `DATABASE_URL` blank to use the `POSTGRES_*` components and keep
`CLICKHOUSE_SECURE=false` with port `8123`.
