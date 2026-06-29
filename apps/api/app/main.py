"""FastAPI application entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, routing, runs, templates, usage, workflows, ws
from app.config import get_settings
from app.db.postgres import SessionLocal
from app.services.template_service import seed_templates

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Idempotently seed gallery templates on startup.
    try:
        with SessionLocal() as db:
            count = seed_templates(db)
            db.commit()
        if count:
            logger.info("seeded %d templates", count)
    except Exception:  # noqa: BLE001 - never block startup on seeding
        logger.warning("template seeding skipped", exc_info=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Stagehand API",
        version="0.1.0",
        description="Trace-first multi-agent workflow platform — backend API.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(workflows.router)
    app.include_router(runs.router)
    app.include_router(routing.router)
    app.include_router(templates.router)
    app.include_router(usage.router)
    app.include_router(ws.router)

    return app


app = create_app()
