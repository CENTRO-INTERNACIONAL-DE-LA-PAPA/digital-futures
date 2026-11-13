import time

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from digital_futures import api
from digital_futures.graph import build_graph


@pytest.fixture
def client(monkeypatch):
    store = InMemoryStore()
    built = build_graph(InMemorySaver(), store), store
    monkeypatch.setattr(api, "backend", lambda: built)
    return TestClient(api.app)


def settled(client, run_id: str) -> dict:
    """Wait for the background work to finish, then return the run."""
    for _ in range(200):
        if not client.get(f"/api/runs/{run_id}/progress").json()["busy"]:
            return client.get(f"/api/runs/{run_id}").json()
        time.sleep(0.01)
    raise AssertionError("the run did not settle")


def test_a_run_goes_from_start_to_review_to_the_next_step(client):
    run_id = client.post("/api/runs", json={"scope": {"geography": "Andes"}}).json()["id"]
    run = settled(client, run_id)
    assert run["pending"]["step"] == "drivers" and run["failed"] is None and run["working"] is None
    assert run["progress"][0]["message"] == "fake search"
    assert client.get("/api/runs").json()[0]["scope"] == {"geography": "Andes"}

    client.post(f"/api/runs/{run_id}/review", json={"action": "approve"})
    run = settled(client, run_id)
    assert run["pending"]["step"] == "clusters" and run["done"] == ["drivers"]

    assert client.post(f"/api/runs/{run_id}/reopen", json={"step": "drivers"}).status_code == 200
    assert client.get(f"/api/runs/{run_id}").json()["pending"]["step"] == "drivers"
    assert client.post(f"/api/runs/{run_id}/reopen", json={"step": "axes"}).status_code == 404


def test_meta_lists_the_steps_in_order(client):
    steps = [s["name"] for s in client.get("/api/meta").json()["steps"]]
    assert steps[0] == "drivers" and steps[-1] == "backcast" and "signals" in steps


def test_metrics_exports_and_comparison_are_served(client):
    run_id = client.post("/api/runs", json={"scope": {}, "hitl": False}).json()["id"]
    settled(client, run_id)
    assert client.get(f"/api/runs/{run_id}/metrics").json()["arm"] == "AI alone"
    report = client.get(f"/api/runs/{run_id}/export.md")
    assert report.text.startswith("# Scenarios for") and "attachment" in report.headers["content-disposition"]
    assert "narratives" in client.get(f"/api/runs/{run_id}/export.json").json()
    [row] = client.get("/api/compare").json()
    assert row["finished"] and row["scenarios"] == 4 and row["arm"] == "AI alone"
