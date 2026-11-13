"""Run metrics and the Markdown export, on a full offline run."""

import pytest
from langchain_core.language_models import FakeListChatModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from digital_futures import runs
from digital_futures.export import to_markdown
from digital_futures.graph import STEPS, build_graph
from digital_futures.llm import CallLog, tally
from digital_futures.metrics import arm, summary


@pytest.fixture
def finished():
    """A run where the human edits the clusters, sends the axes back once, and approves the rest."""
    store = InMemoryStore()
    graph = build_graph(InMemorySaver(), store)
    thread_id = runs.create(store, {"seed_drivers": ["Cognitive debt"]})
    runs.start(graph, store, thread_id, lambda m: None)
    sent_back = False
    while request := runs.pending(graph, thread_id):
        decision = {"action": "approve"}
        if request["step"] == "clusters":
            decision = {"action": "edit", "data": [{**request["data"][0], "name": "Renamed"}, *request["data"][1:]]}
        if request["step"] == "axes" and not sent_back:
            decision, sent_back = {"action": "revise", "feedback": "other poles"}, True
        runs.resume(graph, thread_id, decision, lambda m: None)
    return runs.state(graph, thread_id)


def test_summary_counts_runs_reviews_and_edits_per_step(finished):
    m = summary(finished)
    rows = {r["step"]: r for r in m["steps"]}
    assert m["arm"] == "AI + seed drivers + human review" and m["complete"]
    assert [r["step"] for r in m["steps"]] == [s for s, _, _ in STEPS]
    assert rows["clusters"]["edited"] == 1 and rows["clusters"]["kept"] == {"before": 2, "after": 2, "unchanged": 1}
    assert rows["axes"]["ai_runs"] == 2 and rows["axes"]["revised"] == 1 and rows["axes"]["approved"] == 1
    assert rows["drivers"]["review_seconds"] is not None
    assert m["totals"]["edited"] == 1 and m["totals"]["revised"] == 1 and m["totals"]["scenarios"] == 4


def test_summary_of_an_empty_or_old_run_does_not_fail():
    assert summary({})["totals"]["cost"] == 0
    old = {"reviews": [{"step": "drivers", "action": "approve", "feedback": "", "at": "2026-11-10T10:00:00+00:00"}]}
    old["drivers"] = [{"id": "d1", "name": "Water rights", "description": "x", "steeple": "legal", "sources": []}]
    m = summary(old)
    assert not m["complete"] and not m["steps"][0]["recorded"] and m["steps"][1]["recorded"]
    assert m["steps"][0]["approved"] == 1 and m["steps"][0]["review_seconds"] is None
    assert "| 2 · Drivers of change | 1 |  |  |  |  | 1 | 0 | 0 |  |  |" in to_markdown(old)


def test_arm_names():
    assert arm({}, False) == "AI alone"
    assert arm({"seed_drivers": ["x"]}, False) == "AI + seed drivers alone"


def test_markdown_report_has_scenarios_material_and_process_record(finished):
    text = to_markdown(finished)
    assert text.startswith("# Scenarios for food, land and water systems in Global South, 2065")
    assert "## Matrix 1:" in text and "### World aa" in text and "**Farmer.** I remember…" in text
    assert "### Signals seen today" in text and "[News](http://news)" in text
    assert "## Drivers of change" in text and "## Process record" in text
    assert "Arm: **AI + seed drivers + human review**." in text
    assert "| 3 · Clusters | 2 | 1 | 0 |" in text


def test_tally_counts_parallel_ai_calls():
    model = FakeListChatModel(responses=["a"], callbacks=[CallLog()])
    with tally() as counts:
        list(model.batch_as_completed(["one", "two", "three"]))
    assert counts["ai_calls"] == 3
    model.invoke("outside the block")  # must not fail or be counted
    assert counts["ai_calls"] == 3
