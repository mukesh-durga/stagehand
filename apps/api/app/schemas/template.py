"""Pydantic schemas for templates."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.workflow import WorkflowGraph


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    category: str | None
    tags: list[str]
    graph: WorkflowGraph
    is_public: bool
    created_at: datetime
    updated_at: datetime


class CloneTemplateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
