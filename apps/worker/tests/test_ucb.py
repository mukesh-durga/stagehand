"""Tests for the UCB router and adaptive agent node."""

import math

from sqlalchemy.orm import Session

from worker.ai.ucb_router import compute_ucb_score, select_model
from worker.engine.context import ExecutionContext
from worker.engine.nodes.agent_node import AgentNode
from worker.engine.trace_emitter import TraceEmitter
from worker.models import ModelRoutingStats

CANDIDATES = ["mock-cheap", "mock-strong"]


def _stat(db, route_key, model, pulls, avg_reward):
    row = ModelRoutingStats(
        route_key=route_key,
        model_name=model,
        node_id="ag1",
        pulls=pulls,
        total_reward=avg_reward * pulls,
        average_reward=avg_reward,
    )
    db.add(row)
    db.flush()
    return row


# --- UCB selection ---

def test_selects_untried_cheap_first():
    selected, scores, reason = select_model(None, "rk", CANDIDATES, 1.0)
    assert selected == "mock-cheap"
    assert scores == {}
    assert "untried" in reason


def test_selects_untried_strong_after_cheap(db_session: Session):
    _stat(db_session, "rk1", "mock-cheap", pulls=2, avg_reward=0.5)
    selected, _, reason = select_model(db_session, "rk1", CANDIDATES, 1.0)
    assert selected == "mock-strong"
    assert "untried" in reason


def test_chooses_higher_ucb_when_both_tried(db_session: Session):
    # strong has much higher average reward -> should win
    _stat(db_session, "rk2", "mock-cheap", pulls=5, avg_reward=0.2)
    _stat(db_session, "rk2", "mock-strong", pulls=5, avg_reward=0.9)
    selected, scores, _ = select_model(db_session, "rk2", CANDIDATES, 1.0)
    assert selected == "mock-strong"
    assert scores["mock-strong"] > scores["mock-cheap"]


def test_ucb_score_formula():
    score = compute_ucb_score(average_reward=0.5, pulls=4, total_pulls=10, exploration_weight=1.0)
    expected = 0.5 + math.sqrt(math.log(11) / 4)
    assert abs(score - expected) < 1e-9


# --- adaptive agent node ---

def _context(db: Session) -> ExecutionContext:
    return ExecutionContext(
        run_id="r",
        workflow_id="wf",
        workflow_version_id="ver",
        input={"q": "x"},
        run_config={},
        max_steps=25,
        max_runtime_seconds=120,
        max_cost_usd=0.5,
        emitter=TraceEmitter("r", "wf", "ver"),
        db=db,
    )


def test_adaptive_node_emits_routing_decision(db_session: Session):
    ctx = _context(db_session)
    node = {"id": "ag1", "type": "agent", "config": {"modelPolicy": "adaptive"}}
    out = AgentNode().execute(node, ctx, ctx.input)
    types = [e.event_type for e in ctx.emitter.events]
    assert "routing_decision" in types
    # First decision with no stats -> cheap.
    assert out["model"] == "mock-cheap"
    decision = next(e for e in ctx.emitter.events if e.event_type == "routing_decision")
    assert decision.metadata_json["selected_model"] == "mock-cheap"
    assert decision.metadata_json["route_key"] == "wf:ver:ag1"


def test_cheap_policy_bypasses_ucb(db_session: Session):
    ctx = _context(db_session)
    node = {"id": "ag1", "type": "agent", "config": {"modelPolicy": "cheap"}}
    out = AgentNode().execute(node, ctx, ctx.input)
    assert out["model"] == "mock-cheap"
    assert "routing_decision" not in [e.event_type for e in ctx.emitter.events]


def test_strong_policy_bypasses_ucb(db_session: Session):
    ctx = _context(db_session)
    node = {"id": "ag1", "type": "agent", "config": {"modelPolicy": "strong"}}
    out = AgentNode().execute(node, ctx, ctx.input)
    assert out["model"] == "mock-strong"
    assert "routing_decision" not in [e.event_type for e in ctx.emitter.events]
