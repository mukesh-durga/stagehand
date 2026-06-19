"""Tests for workflow CRUD, versioning, and graph validation."""

import uuid
from typing import Any

from fastapi.testclient import TestClient


def valid_graph() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "in1", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "out1", "type": "output", "position": {"x": 200, "y": 0}, "config": {}},
        ],
        "edges": [{"id": "e1", "source": "in1", "target": "out1"}],
    }


def create_payload(name: str = "WF") -> dict[str, Any]:
    return {"name": name, "description": "desc", "graph": valid_graph()}


def _create(client: TestClient, name: str = "WF") -> dict[str, Any]:
    resp = client.post("/workflows", json=create_payload(name))
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- happy path ---

def test_create_workflow(client: TestClient) -> None:
    data = _create(client)
    assert data["name"] == "WF"
    assert data["current_version_number"] == 1
    assert data["current_version_id"]
    assert len(data["graph"]["nodes"]) == 2


def test_list_workflows(client: TestClient) -> None:
    _create(client, "A")
    _create(client, "B")
    resp = client.get("/workflows")
    assert resp.status_code == 200
    names = [w["name"] for w in resp.json()]
    assert "A" in names and "B" in names


def test_get_workflow_by_id(client: TestClient) -> None:
    wf_id = _create(client)["id"]
    resp = client.get(f"/workflows/{wf_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wf_id


def test_get_workflow_not_found(client: TestClient) -> None:
    resp = client.get(f"/workflows/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_update_name_and_description(client: TestClient) -> None:
    wf_id = _create(client)["id"]
    resp = client.put(f"/workflows/{wf_id}", json={"name": "New", "description": "nd"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New"
    assert body["description"] == "nd"
    # Graph untouched -> still version 1.
    assert body["current_version_number"] == 1


def test_update_graph_creates_new_version(client: TestClient) -> None:
    wf_id = _create(client)["id"]
    graph = valid_graph()
    graph["nodes"].append(
        {"id": "agent1", "type": "agent", "position": {"x": 100, "y": 0}, "config": {}}
    )
    graph["edges"] = [
        {"id": "e1", "source": "in1", "target": "agent1"},
        {"id": "e2", "source": "agent1", "target": "out1"},
    ]
    resp = client.put(f"/workflows/{wf_id}", json={"graph": graph})
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_version_number"] == 2
    assert len(body["graph"]["nodes"]) == 3


def test_list_versions(client: TestClient) -> None:
    wf_id = _create(client)["id"]
    client.put(f"/workflows/{wf_id}", json={"graph": valid_graph()})
    resp = client.get(f"/workflows/{wf_id}/versions")
    assert resp.status_code == 200
    versions = resp.json()
    assert [v["version_number"] for v in versions] == [1, 2]


def test_delete_workflow(client: TestClient) -> None:
    wf_id = _create(client)["id"]
    resp = client.delete(f"/workflows/{wf_id}")
    assert resp.status_code == 204
    assert client.get(f"/workflows/{wf_id}").status_code == 404


# --- graph validation (semantic -> 400) ---

def test_invalid_graph_no_input_rejected(client: TestClient) -> None:
    graph = valid_graph()
    graph["nodes"] = [n for n in graph["nodes"] if n["type"] != "input"]
    graph["edges"] = []
    resp = client.post("/workflows", json={"name": "x", "graph": graph})
    assert resp.status_code == 400


def test_invalid_graph_no_output_rejected(client: TestClient) -> None:
    graph = valid_graph()
    graph["nodes"] = [n for n in graph["nodes"] if n["type"] != "output"]
    graph["edges"] = []
    resp = client.post("/workflows", json={"name": "x", "graph": graph})
    assert resp.status_code == 400


def test_duplicate_node_ids_rejected(client: TestClient) -> None:
    graph = valid_graph()
    graph["nodes"][1]["id"] = "in1"  # collide with the input node id
    graph["edges"] = [{"id": "e1", "source": "in1", "target": "in1"}]
    resp = client.post("/workflows", json={"name": "x", "graph": graph})
    assert resp.status_code == 400


def test_duplicate_edge_ids_rejected(client: TestClient) -> None:
    graph = valid_graph()
    graph["nodes"].append(
        {"id": "agent1", "type": "agent", "position": {"x": 1, "y": 1}, "config": {}}
    )
    graph["edges"] = [
        {"id": "e1", "source": "in1", "target": "agent1"},
        {"id": "e1", "source": "agent1", "target": "out1"},
    ]
    resp = client.post("/workflows", json={"name": "x", "graph": graph})
    assert resp.status_code == 400


def test_edge_referencing_missing_node_rejected(client: TestClient) -> None:
    graph = valid_graph()
    graph["edges"] = [{"id": "e1", "source": "in1", "target": "ghost"}]
    resp = client.post("/workflows", json={"name": "x", "graph": graph})
    assert resp.status_code == 400


def test_invalid_node_type_returns_422(client: TestClient) -> None:
    graph = valid_graph()
    graph["nodes"][0]["type"] = "banana"
    resp = client.post("/workflows", json={"name": "x", "graph": graph})
    assert resp.status_code == 422
