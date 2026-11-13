"""Saved step results, so that going back to an earlier review costs nothing.

Each step's result is saved in the store under a hash of the step's inputs. When the step is
reached again with the same inputs (the reviewer went back and changed nothing before it), the
saved result is reused instead of calling the AI. Results are saved per run.
"""

import hashlib
import json

from langgraph.config import get_config, get_store

from digital_futures.config import settings


def digest(step: str, inputs: dict, source: str = "") -> str:
    """Hash of everything a step's result depends on: its inputs, the models in use, and the
    step's own code (`source`), so that a changed prompt does not return old results."""
    models = [settings.reasoning_model, settings.narrative_model, settings.reasoning_effort]
    text = json.dumps([step, models, inputs, source], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def _namespace() -> tuple[str, str]:
    return ("cache", get_config()["configurable"]["thread_id"])


def load(key: str | None):
    """The saved result, or None. Also None when the graph runs without a store."""
    store = get_store()
    item = store.get(_namespace(), key) if store and key else None
    return item.value["data"] if item else None


def save(key: str | None, data) -> None:
    store = get_store()
    if store and key:
        store.put(_namespace(), key, {"data": data})
