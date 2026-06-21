"""Tests for the template gallery (Milestone 16)."""

from fastapi.testclient import TestClient

from app.db.models.template import Template
from app.services.template_service import TEMPLATE_SEEDS, seed_templates

SEED_SLUGS = {s["slug"] for s in TEMPLATE_SEEDS}


def test_list_templates_returns_seeded(client: TestClient) -> None:
    resp = client.get("/templates")
    assert resp.status_code == 200
    slugs = {t["slug"] for t in resp.json()}
    assert SEED_SLUGS.issubset(slugs)


def test_get_template_by_slug(client: TestClient) -> None:
    resp = client.get("/templates/basic-agent")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "basic-agent"
    assert body["graph"]["nodes"]


def test_get_missing_template_404(client: TestClient) -> None:
    assert client.get("/templates/does-not-exist").status_code == 404


def test_clone_creates_workflow_with_current_version(client: TestClient) -> None:
    resp = client.post("/templates/basic-agent/clone")
    assert resp.status_code == 201, resp.text
    wf = resp.json()
    assert wf["id"]
    assert wf["current_version_id"] is not None
    assert wf["current_version_number"] == 1


def test_cloned_graph_matches_template(client: TestClient) -> None:
    template = client.get("/templates/tool-calculator").json()
    wf = client.post("/templates/tool-calculator/clone").json()
    # Same structure (node/edge ids and types).
    t_nodes = {(n["id"], n["type"]) for n in template["graph"]["nodes"]}
    w_nodes = {(n["id"], n["type"]) for n in wf["graph"]["nodes"]}
    assert t_nodes == w_nodes
    assert len(template["graph"]["edges"]) == len(wf["graph"]["edges"])


def test_cloned_workflow_opens_via_workflow_endpoint(client: TestClient) -> None:
    wf = client.post("/templates/adaptive-agent/clone", json={"name": "My Adaptive"}).json()
    fetched = client.get(f"/workflows/{wf['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "My Adaptive"


def test_clone_missing_template_404(client: TestClient) -> None:
    assert client.post("/templates/nope/clone").status_code == 404


def test_seed_is_idempotent(client: TestClient, db_session) -> None:
    # Templates already seeded (startup). Re-seeding inserts nothing.
    before = db_session.query(Template).filter(Template.slug == "basic-agent").count()
    seed_templates(db_session)
    seed_templates(db_session)
    after = db_session.query(Template).filter(Template.slug == "basic-agent").count()
    assert before == 1
    assert after == 1
