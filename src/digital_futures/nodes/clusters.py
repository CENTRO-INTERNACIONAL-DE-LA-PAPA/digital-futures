"""Node 3: cluster drivers. TODO(phase 4): deepagent + rubric."""

from digital_futures.state import State


def clusters(state: State) -> dict:
    by_steeple: dict[str, list[str]] = {}
    for d in state["drivers"]:
        by_steeple.setdefault(d["steeple"], []).append(d["id"])
    return {
        "clusters": [
            {"name": s.title(), "rationale": "Stub: grouped by STEEPLE", "driver_ids": ids}
            for s, ids in by_steeple.items()
        ]
    }
