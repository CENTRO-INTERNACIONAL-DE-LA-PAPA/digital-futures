"""Start, list and resume scenario runs. Each run is a LangGraph thread, registered in the store."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from langgraph.store.base import BaseStore
from langgraph.types import Command

NAMESPACE = ("runs",)


def config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


Progress = Callable[[str], None]


def _run(graph, payload, thread_id: str, on_progress: Progress) -> None:
    """Run until the next review (or the end), passing node progress messages on."""
    for event in graph.stream(payload, config(thread_id), stream_mode="custom"):
        on_progress(event["progress"])


def start(graph, store: BaseStore, scope: dict | None = None, hitl: bool = True, on_progress: Progress = print) -> str:
    thread_id = str(uuid.uuid4())
    store.put(NAMESPACE, thread_id, {"created": datetime.now(UTC).isoformat(), "scope": scope or {}, "hitl": hitl})
    _run(graph, {"scope": scope or {}, "hitl": hitl}, thread_id, on_progress)
    return thread_id


def resume(graph, thread_id: str, decision: dict, on_progress: Progress = print) -> None:
    _run(graph, Command(resume=decision), thread_id, on_progress)


def reopen(graph, thread_id: str, step: str) -> None:
    """Go back to the review of `step`, keeping its latest output; later steps will run again.

    Forks the run from the checkpoint where that review was waiting, so no AI step is re-run.
    The old branch stays in the checkpoint history.
    """
    for snapshot in graph.get_state_history(config(thread_id)):
        if snapshot.next == (f"review_{step}",):
            graph.update_state(snapshot.config, {}, as_node=step)
            _run(graph, None, thread_id, lambda message: None)
            return
    raise ValueError(f"Step {step!r} has not been reached in run {thread_id}")


def state(graph, thread_id: str) -> dict:
    return graph.get_state(config(thread_id)).values


def pending(graph, thread_id: str) -> dict | None:
    """The review the run is waiting for ({"step", "data"}), or None."""
    interrupts = graph.get_state(config(thread_id)).interrupts
    return interrupts[0].value if interrupts else None


def listing(store: BaseStore) -> list[tuple[str, dict]]:
    items = store.search(NAMESPACE, limit=200)
    return sorted(((i.key, i.value) for i in items), key=lambda kv: kv[1]["created"], reverse=True)
