import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from digital_futures import runs
from digital_futures.graph import build_graph
from digital_futures.progress import reporter


def test_progress_reaches_the_caller_and_run_is_registered():
    store = InMemoryStore()
    graph = build_graph(InMemorySaver(), store)
    messages = []
    thread_id = runs.create(store)
    runs.start(graph, store, thread_id, on_progress=messages.append)
    assert messages == ["fake search"]
    assert runs.pending(graph, thread_id)["step"] == "drivers"
    assert runs.listing(store)[0][0] == thread_id


def test_reporter_is_silent_outside_a_graph():
    reporter()("nobody listens")  # must not raise


def test_reopen_goes_back_to_an_earlier_review_without_rerunning_it():
    store = InMemoryStore()
    graph = build_graph(InMemorySaver(), store)
    messages = []
    thread_id = runs.create(store)
    runs.start(graph, store, thread_id, on_progress=messages.append)
    runs.resume(graph, thread_id, {"action": "revise", "feedback": "v2"}, messages.append)
    while request := runs.pending(graph, thread_id):
        runs.resume(graph, thread_id, {"action": "approve"}, messages.append)
    assert runs.state(graph, thread_id)["narratives"]

    runs.reopen(graph, thread_id, "drivers")

    assert runs.pending(graph, thread_id)["step"] == "drivers"
    values = runs.state(graph, thread_id)
    assert "v2" in values["drivers"][0]["description"]  # latest version kept
    assert "clusters" not in values
    assert messages == ["fake search", "fake search"]  # the AI step was not re-run


def test_reopen_unknown_step_fails():
    store = InMemoryStore()
    graph = build_graph(InMemorySaver(), store)
    thread_id = runs.create(store)
    runs.start(graph, store, thread_id, on_progress=lambda m: None)
    with pytest.raises(ValueError):
        runs.reopen(graph, thread_id, "axes")


def test_failed_step_is_reported_and_retry_runs_only_that_step(monkeypatch):
    import importlib

    clusters_node = importlib.import_module("digital_futures.nodes.clusters")
    real = clusters_node.research
    calls = []

    def flaky(prompt, drivers):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("provider hiccup")
        return real(prompt, drivers)

    monkeypatch.setattr(clusters_node, "research", flaky)
    store = InMemoryStore()
    graph = build_graph(InMemorySaver(), store)
    messages = []
    thread_id = runs.create(store)
    runs.start(graph, store, thread_id, on_progress=messages.append)

    with pytest.raises(RuntimeError):
        runs.resume(graph, thread_id, {"action": "approve"}, messages.append)
    step, error = runs.failed(graph, thread_id)
    assert step == "clusters" and "provider hiccup" in error
    assert runs.pending(graph, thread_id) is None

    runs.retry(graph, thread_id, messages.append)
    assert runs.failed(graph, thread_id) is None
    assert runs.pending(graph, thread_id)["step"] == "clusters"
    assert messages == ["fake search"]  # drivers were not searched again
