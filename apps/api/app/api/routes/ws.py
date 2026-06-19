"""WebSocket live trace streaming.

WS /ws/runs/{run_id} replays and streams a run's trace events from the Redis list
`run:{run_id}:events` (written by the worker in Milestone 7). Events already present
when a client connects are sent first (catch-up), then new events are streamed as
they arrive. The connection closes once a terminal event (run_completed/run_failed)
is delivered.
"""

import asyncio
import json
import logging
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.models.run import WorkflowRun
from app.db.postgres import get_db
from app.db.redis import get_async_redis, run_events_key

logger = logging.getLogger(__name__)

router = APIRouter()

_POLL_INTERVAL_SECONDS = 0.3
_TERMINAL_EVENTS = {"run_completed", "run_failed"}


@router.websocket("/ws/runs/{run_id}")
async def ws_run_trace(
    websocket: WebSocket,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_async_redis),
) -> None:
    await websocket.accept()

    if db.get(WorkflowRun, run_id) is None:
        await websocket.send_json({"type": "error", "detail": "Run not found"})
        await websocket.close(code=4404)
        return

    await websocket.send_json({"type": "connected", "run_id": str(run_id)})

    key = run_events_key(str(run_id))
    sent = 0
    try:
        while True:
            try:
                length = await redis_client.llen(key)
            except Exception:  # noqa: BLE001 - tolerate transient Redis errors
                logger.debug("redis llen failed; retrying", exc_info=True)
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                continue

            if length > sent:
                items = await redis_client.lrange(key, sent, length - 1)
                for raw in items:
                    sent += 1
                    try:
                        event = json.loads(raw)
                    except (TypeError, ValueError):
                        continue
                    await websocket.send_json(event)
                    if event.get("event_type") in _TERMINAL_EVENTS:
                        await websocket.close()
                        return

            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001 - never crash the server on a socket error
        logger.warning("websocket trace stream error", exc_info=True)
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
