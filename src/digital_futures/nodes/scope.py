"""Node 1: thematic, geographic and temporal scope. No LLM: defaults or form input."""

from digital_futures.state import Scope, State

DEFAULT_SCOPE: Scope = {
    "theme": "food, land and water systems",
    "geography": "Global South",
    "current_year": 2026,
    "horizon_year": 2065,
    "seed_drivers": [],
    "target_drivers": 80,
}


def scope(state: State) -> dict:
    return {"scope": {**DEFAULT_SCOPE, **state.get("scope", {})}, "hitl": state.get("hitl", True)}
