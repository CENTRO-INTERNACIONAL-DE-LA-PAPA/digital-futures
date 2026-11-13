"""End-to-end runs of the stub graph with simulated human answers."""

import uuid

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from digital_futures.graph import STEPS, build_graph

STEP_NAMES = [s for s, _, _ in STEPS]


def run(answers: dict[str, list[dict]], start: dict | None = None):
    """Run to the end; `answers[step]` is consumed in order, default approve."""
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    seen = []
    result = graph.invoke(start or {}, config)
    while interrupts := result.get("__interrupt__"):
        step = interrupts[0].value["step"]
        seen.append(step)
        queue = answers.get(step, [])
        result = graph.invoke(Command(resume=queue.pop(0) if queue else {"action": "approve"}), config)
    return result, seen


def test_approve_all_visits_every_step_once():
    result, seen = run({})
    assert seen == STEP_NAMES
    assert result["narratives"]
    assert [r["step"] for r in result["reviews"]] == STEP_NAMES


def test_revise_reruns_step_with_feedback():
    result, seen = run({"drivers": [{"action": "revise", "feedback": "more water drivers"}]})
    assert seen[:2] == ["drivers", "drivers"]
    assert "more water drivers" in result["drivers"][0]["description"]
    assert result["feedback"] is None


def test_edit_replaces_output():
    edited = [{"id": i, "name": f"Only {i}", "description": "", "steeple": "legal", "sources": []} for i in ("x", "y")]
    result, _ = run({"drivers": [{"action": "edit", "data": edited}]})
    assert result["drivers"] == edited
    assert result["clusters"][0]["driver_ids"] == ["x"]


def test_seed_drivers_and_scope_override():
    result, _ = run({}, {"scope": {"horizon_year": 2050, "seed_drivers": ["Cognitive debt"]}})
    assert result["scope"]["horizon_year"] == 2050
    assert result["scope"]["geography"] == "Global South"
    assert "Cognitive debt" in result["drivers"][0]["description"]


def test_without_hitl_runs_straight_through():
    result, seen = run({}, {"hitl": False})
    assert seen == []
    assert result["narratives"]


def test_unknown_action_fails():
    with pytest.raises(ValueError):
        run({"drivers": [{"action": "maybe"}]})
