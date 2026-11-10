"""Start, list and resume scenario runs. Each run is a LangGraph thread, registered in the store."""

import uuid
from datetime import UTC, datetime

from langgraph.store.base import BaseStore
from langgraph.types import Command

NAMESPACE = ("runs",)


def config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def start(graph, store: BaseStore, scope: dict | None = None, hitl: bool = True) -> str:
    thread_id = str(uuid.uuid4())
    store.put(NAMESPACE, thread_id, {"created": datetime.now(UTC).isoformat(), "scope": scope or {}, "hitl": hitl})
    graph.invoke({"scope": scope or {}, "hitl": hitl}, config(thread_id))
    return thread_id


def resume(graph, thread_id: str, decision: dict) -> None:
    graph.invoke(Command(resume=decision), config(thread_id))


def pending(graph, thread_id: str) -> dict | None:
    """The review the run is waiting for ({"step", "data"}), or None."""
    interrupts = graph.get_state(config(thread_id)).interrupts
    return interrupts[0].value if interrupts else None


def listing(store: BaseStore) -> list[tuple[str, dict]]:
    items = store.search(NAMESPACE, limit=200)
    return sorted(((i.key, i.value) for i in items), key=lambda kv: kv[1]["created"], reverse=True)
