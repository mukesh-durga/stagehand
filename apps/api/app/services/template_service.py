"""Template gallery: seed data, queries, and cloning into a workflow."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.template import Template
from app.schemas.template import TemplateResponse
from app.schemas.workflow import WorkflowCreate, WorkflowGraph, WorkflowResponse
from app.services import workflow_service


class TemplateNotFoundError(Exception):
    """Raised when a template slug cannot be found (-> HTTP 404)."""


def _io(node_id: str, node_type: str, x: int, label: str, **config: Any) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "position": {"x": x, "y": 0},
        "config": {"label": label, **config},
    }


def _edge(edge_id: str, source: str, target: str) -> dict[str, Any]:
    return {"id": edge_id, "source": source, "target": target}


# Canonical seed templates. Each graph matches the builder/workflow schema.
TEMPLATE_SEEDS: list[dict[str, Any]] = [
    {
        "slug": "basic-agent",
        "name": "Basic Agent",
        "description": "Input → Agent → Output. A simple text-generation workflow.",
        "category": "Starter",
        "tags": ["agent", "starter"],
        "graph": {
            "nodes": [
                _io("in1", "input", 0, "Input"),
                _io("ag1", "agent", 220, "Agent", prompt="Summarize the input.", modelPolicy="cheap"),
                _io("out1", "output", 440, "Output"),
            ],
            "edges": [_edge("e1", "in1", "ag1"), _edge("e2", "ag1", "out1")],
        },
    },
    {
        "slug": "tool-calculator",
        "name": "Tool Calculator",
        "description": "Input → Tool(calculator) → Output. Evaluates an arithmetic expression.",
        "category": "Tools",
        "tags": ["tool", "calculator"],
        "graph": {
            "nodes": [
                _io("in1", "input", 0, "Input"),
                _io("t1", "tool", 220, "Calculator", toolName="calculator", expression="2 + 3 * 4"),
                _io("out1", "output", 440, "Output"),
            ],
            "edges": [_edge("e1", "in1", "t1"), _edge("e2", "t1", "out1")],
        },
    },
    {
        "slug": "agent-with-retry",
        "name": "Agent With Retry",
        "description": "Agent with retries and a fallback model — demonstrates retry/fallback traces.",
        "category": "Reliability",
        "tags": ["agent", "retry", "fallback"],
        "graph": {
            "nodes": [
                _io("in1", "input", 0, "Input"),
                _io(
                    "ag1",
                    "agent",
                    220,
                    "Agent",
                    prompt="Answer the question.",
                    modelPolicy="cheap",
                    maxRetries=2,
                    fallbackModel="strong",
                    failTimes=1,
                ),
                _io("out1", "output", 440, "Output"),
            ],
            "edges": [_edge("e1", "in1", "ag1"), _edge("e2", "ag1", "out1")],
        },
    },
    {
        "slug": "adaptive-agent",
        "name": "Adaptive Agent",
        "description": "Agent using adaptive (UCB) model routing between cheap and strong.",
        "category": "Routing",
        "tags": ["agent", "adaptive", "ucb"],
        "graph": {
            "nodes": [
                _io("in1", "input", 0, "Input"),
                _io("ag1", "agent", 220, "Agent", prompt="Help the user.", modelPolicy="adaptive"),
                _io("out1", "output", 440, "Output"),
            ],
            "edges": [_edge("e1", "in1", "ag1"), _edge("e2", "ag1", "out1")],
        },
    },
]


def seed_templates(db: Session) -> int:
    """Insert any missing seed templates. Idempotent (keyed by slug)."""
    inserted = 0
    for seed in TEMPLATE_SEEDS:
        exists = db.scalar(select(Template.id).where(Template.slug == seed["slug"]))
        if exists is not None:
            continue
        db.add(
            Template(
                name=seed["name"],
                slug=seed["slug"],
                description=seed["description"],
                category=seed["category"],
                tags=seed["tags"],
                graph_json=seed["graph"],
                is_public=True,
            )
        )
        inserted += 1
    db.flush()
    return inserted


def _to_response(template: Template) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        tags=list(template.tags or []),
        graph=template.graph_json,
        is_public=template.is_public,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def list_templates(db: Session) -> list[TemplateResponse]:
    stmt = (
        select(Template)
        .where(Template.is_public.is_(True))
        .order_by(Template.category, Template.name)
    )
    return [_to_response(t) for t in db.scalars(stmt)]


def get_template_by_slug(db: Session, slug: str) -> TemplateResponse:
    template = db.scalar(select(Template).where(Template.slug == slug))
    if template is None:
        raise TemplateNotFoundError(slug)
    return _to_response(template)


def clone_template(
    db: Session, slug: str, name: str | None = None, description: str | None = None
) -> WorkflowResponse:
    template = db.scalar(select(Template).where(Template.slug == slug))
    if template is None:
        raise TemplateNotFoundError(slug)

    # Reuse workflow creation (validates graph, creates v1, sets current version).
    payload = WorkflowCreate(
        name=name or template.name,
        description=description if description is not None else template.description,
        graph=WorkflowGraph(**template.graph_json),
    )
    return workflow_service.create_workflow(db, payload)
