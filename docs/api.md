# API

Placeholder. The REST and WebSocket API surface is implemented starting in
Milestone 1 (health) and expanded through later milestones.

Planned endpoints (see section 8.3 of `STAGEHAND_PROJECT.md`):

- `GET /health`
- Workflows: `POST/GET/PUT/DELETE /workflows`, versions
- Runs: `POST /workflows/{id}/run`, `GET /runs`, `GET /runs/{id}`, trace, replay, diff
- Evals: `POST/GET /runs/{id}/eval`
- Templates: `GET/POST /templates`, clone
- WebSocket: `WS /ws/runs/{run_id}`

This document will be filled in as endpoints are built.
