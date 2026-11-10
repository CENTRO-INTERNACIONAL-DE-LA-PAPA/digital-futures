from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from digital_futures import runs
from digital_futures.graph import build_graph
from digital_futures.progress import reporter


def test_progress_reaches_the_caller_and_run_is_registered():
    store = InMemoryStore()
    graph = build_graph(InMemorySaver(), store)
    messages = []
    thread_id = runs.start(graph, store, on_progress=messages.append)
    assert messages == ["fake search"]
    assert runs.pending(graph, thread_id)["step"] == "drivers"
    assert runs.listing(store)[0][0] == thread_id


def test_reporter_is_silent_outside_a_graph():
    reporter()("nobody listens")  # must not raise
