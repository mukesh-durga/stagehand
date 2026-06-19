# Deployment

Placeholder. See sections 18 and 24 of `STAGEHAND_PROJECT.md` for the full plan.

## Target topology

- Frontend → Vercel
- Backend API → Render / Fly.io / Railway
- Worker → Render / Fly.io / Railway background worker
- PostgreSQL → Neon or Supabase
- Redis → Upstash
- ClickHouse → Local Docker first, ClickHouse Cloud later

Local development uses Docker Compose for Postgres, Redis, and ClickHouse only;
API, worker, and frontend run on the host during development.

This document will be filled in at the deployment milestone.
