"""Tests for run creation and retrieval (Milestone 5)."""

import json
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db.redis import RUN_QUEUE_KEY, get_redis
from app.main import app


class FakeRedis:
    """Captures rpush calls so tests can assert on the enqueued job."""

    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}

    def rpush(self, key: str, value: str) -> int:
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])


@pytest.fixture
def fake_redis() -> FakeRedis:
    fake = FakeRedis()
    app.dependency_overrides[get_redis] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_redis, None)


def valid_graph() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "in1", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "out1", "type": "output", "position": {"x": 200, "y": 0}, "config": {}},
        ],
        "edges": [{"id": "e1", "source": "in1", "target": "out1"}],
    }


def _create_workflow(client: TestClient) -> dict[str, Any]:
    resp = client.post(
        "/workflows",
        json={"name": "Runnable", "description": "d", "graph": valid_graph()},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_run_success(client: TestClient, fake_redis: FakeRedis) -> None:
    wf = _create_workflow(client)
    resp = client.post(f"/workflows/{wf['id']}/run", json={"input": {"query": "hi"}})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "queued"
    assert body["workflow_id"] == wf["id"]


def test_create_run_missing_workflow_404(client: TestClient, fake_redis: FakeRedis) -> None:
    resp = client.post(f"/workflows/{uuid.uuid4()}/run", json={"input": {}})
    assert resp.status_code == 404


def test_create_run_stores_queued_status(client: TestClient, fake_redis: FakeRedis) -> None:
    wf = _create_workflow(client)
    run_id = client.post(f"/workflows/{wf['id']}/run", json={"input": {}}).json()["id"]
    fetched = client.get(f"/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "queued"


def test_create_run_uses_current_version(client: TestClient, fake_redis: FakeRedis) -> None:
    wf = _create_workflow(client)
    body = client.post(f"/workflows/{wf['id']}/run", json={"input": {}}).json()
    assert body["workflow_version_id"] == wf["current_version_id"]


def test_create_run_saves_input(client: TestClient, fake_redis: FakeRedis) -> None:
    wf = _create_workflow(client)
    body = client.post(
        f"/workflows/{wf['id']}/run", json={"input": {"query": "compare X and Y"}}
    ).json()
    assert body["input"] == {"query": "compare X and Y"}


def test_get_run_by_id(client: TestClient, fake_redis: FakeRedis) -> None:
    wf = _create_workflow(client)
    run_id = client.post(f"/workflows/{wf['id']}/run", json={"input": {}}).json()["id"]
    resp = client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


def test_get_run_not_found(client: TestClient) -> None:
    assert client.get(f"/runs/{uuid.uuid4()}").status_code == 404


def test_list_runs(client: TestClient, fake_redis: FakeRedis) -> None:
    wf = _create_workflow(client)
    client.post(f"/workflows/{wf['id']}/run", json={"input": {}})
    client.post(f"/workflows/{wf['id']}/run", json={"input": {}})
    resp = client.get("/runs")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_list_runs_filtered_by_workflow_id(client: TestClient, fake_redis: FakeRedis) -> None:
    wf_a = _create_workflow(client)
    wf_b = _create_workflow(client)
    client.post(f"/workflows/{wf_a['id']}/run", json={"input": {}})

    resp = client.get("/runs", params={"workflow_id": wf_a["id"]})
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) == 1
    assert all(r["workflow_id"] == wf_a["id"] for r in runs)

    assert client.get("/runs", params={"workflow_id": wf_b["id"]}).json() == []


def test_redis_enqueue_called_with_payload(
    client: TestClient, fake_redis: FakeRedis
) -> None:
    wf = _create_workflow(client)
    body = client.post(
        f"/workflows/{wf['id']}/run", json={"input": {"query": "go"}}
    ).json()

    assert RUN_QUEUE_KEY in fake_redis.lists
    assert len(fake_redis.lists[RUN_QUEUE_KEY]) == 1

    job = json.loads(fake_redis.lists[RUN_QUEUE_KEY][0])
    assert job["run_id"] == body["id"]
    assert job["workflow_id"] == wf["id"]
    assert job["workflow_version_id"] == wf["current_version_id"]
    assert job["input"] == {"query": "go"}
    assert job["run_config"] == {
        "max_steps": 25,
        "max_cost_usd": 0.5,
        "max_runtime_seconds": 120,
    }
    assert "created_at" in job


def test_run_config_overrides(client: TestClient, fake_redis: FakeRedis) -> None:
    wf = _create_workflow(client)
    client.post(
        f"/workflows/{wf['id']}/run",
        json={"input": {}, "run_config": {"max_steps": 5, "max_cost_usd": 0.01}},
    )
    job = json.loads(fake_redis.lists[RUN_QUEUE_KEY][0])
    assert job["run_config"]["max_steps"] == 5
    assert job["run_config"]["max_cost_usd"] == 0.01
    # unspecified field falls back to settings default
    assert job["run_config"]["max_runtime_seconds"] == 120
