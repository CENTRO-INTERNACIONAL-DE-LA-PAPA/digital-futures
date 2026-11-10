"""Node 2: identify drivers of change. TODO(phase 3): Opus + Tavily + Asta."""

from digital_futures.state import State


def drivers(state: State) -> dict:
    seeds = state["scope"]["seed_drivers"]
    names = seeds + ["Pollinator decline", "Data-centre water demand", "Rural out-migration", "Soil carbon markets"]
    steeple = ["environmental", "technological", "social", "economic"]
    note = f" (revised: {state['feedback']})" if state.get("feedback") else ""
    return {
        "drivers": [
            {"id": f"d{i}", "name": n, "description": f"Stub driver{note}", "steeple": steeple[i % 4], "sources": []}
            for i, n in enumerate(names, 1)
        ]
    }
