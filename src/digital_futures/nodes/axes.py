"""Node 6: axes of uncertainty. TODO(phase 6): deepagent + rubric (neutral, single-trait poles)."""

from itertools import combinations

from digital_futures.state import State


def axes(state: State) -> dict:
    def axis(driver_id: str) -> dict:
        return {"driver_id": driver_id, "pole_a": f"{driver_id} state A", "pole_b": f"{driver_id} state B"}

    pairs = list(combinations([c["driver_id"] for c in state["critical"]], 2))[:3]
    return {"axis_sets": [{"name": f"{x} × {y}", "x": axis(x), "y": axis(y)} for x, y in pairs]}
