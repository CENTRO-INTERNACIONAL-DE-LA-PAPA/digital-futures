"""Node 7: all four quadrants of every axis set. TODO(phase 6): Opus."""

from digital_futures.state import State


def quadrants(state: State) -> dict:
    return {
        "quadrants": [
            {"axis_set": s["name"], "x_pole": xp, "y_pole": yp, "title": f"{xp} / {yp}", "sketch": "Stub"}
            for s in state["axis_sets"]
            for xp in (s["x"]["pole_a"], s["x"]["pole_b"])
            for yp in (s["y"]["pole_a"], s["y"]["pole_b"])
        ]
    }
