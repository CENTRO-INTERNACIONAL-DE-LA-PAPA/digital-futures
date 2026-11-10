"""Node 8: scenario narratives from four viewpoints. TODO(phase 7): Gemini."""

from digital_futures.state import State

PERSONAS = ["farmer", "community leader", "scientist", "policy maker"]


def narratives(state: State) -> dict:
    return {
        "narratives": [
            {"quadrant": q["title"], "title": q["title"], "personas": {p: "Stub" for p in PERSONAS}}
            for q in state["quadrants"]
        ]
    }
